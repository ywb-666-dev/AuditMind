"""
文件上传路由
支持财务文件上传和解析 - 支持每年多文件上传（结构化+非结构化）
"""
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
import io
import json

from backend.core.database import get_db
from backend.core.security import get_current_user
from backend.models.database import User
from backend.services.file_parser import parse_financial_file, merge_parsed_results

router = APIRouter(prefix="/upload", tags=["文件上传"])


@router.post("/financial-files-v2")
async def upload_financial_files_v2(
    files: List[UploadFile] = File(...),
    year_mapping: str = Form(...),  # JSON字符串，如 {"2023": [0, 1], "2022": [2, 3]} 表示文件索引映射
    company_name: str = Form(...),
    stock_code: Optional[str] = Form(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    上传财务文件批量解析 - 支持每年多文件（结构化+非结构化文档）

    - files: 所有文件列表
    - year_mapping: 年份到文件索引的映射，JSON格式，如 {"2023": [0, 1], "2022": [2]}
      表示2023年有files[0]和files[1]两个文件，2022年有files[2]一个文件
    - company_name: 企业名称
    - stock_code: 证券代码（可选）
    """
    try:
        year_file_map = json.loads(year_mapping)
        # 验证映射有效性
        all_indices = []
        for year, indices in year_file_map.items():
            if not isinstance(indices, list):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"年份{year}的文件索引必须是数组"
                )
            all_indices.extend(indices)

        # 检查索引范围
        if max(all_indices, default=-1) >= len(files) or min(all_indices, default=0) < 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="文件索引超出范围"
            )

    except json.JSONDecodeError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="year_mapping参数格式错误，应为JSON对象"
        )

    results = []
    errors = []

    # 按年份处理文件
    for year, file_indices in year_file_map.items():
        year_files = []
        year_errors = []
        parsed_results_for_year = []

        for idx in file_indices:
            file = files[idx]

            # 检查文件类型
            allowed_extensions = ['.pdf', '.xlsx', '.xls', '.docx', '.doc', '.txt', '.csv']
            if not any(file.filename.lower().endswith(ext) for ext in allowed_extensions):
                year_errors.append(f"文件 {file.filename} 格式不支持")
                continue

            try:
                # 读取文件内容
                content = await file.read()

                # 解析文件
                parse_result = parse_financial_file(
                    file_content=content,
                    filename=file.filename,
                    year=int(year)
                )

                # 添加文件信息
                parse_result["original_filename"] = file.filename
                parse_result["file_size"] = len(content)

                parsed_results_for_year.append(parse_result)
                year_files.append(file.filename)

            except Exception as e:
                error_msg = f"文件 {file.filename} 解析失败: {str(e)}"
                year_errors.append(error_msg)
                errors.append(error_msg)

            finally:
                await file.close()

        # 合并同一年份的所有文件解析结果
        if parsed_results_for_year:
            merged_result = merge_parsed_results(parsed_results_for_year, int(year))
            merged_result["year"] = int(year)
            merged_result["files_count"] = len(parsed_results_for_year)
            merged_result["file_names"] = year_files
            results.append(merged_result)
        else:
            # 该年份没有成功解析的文件
            results.append({
                "year": int(year),
                "parsed_success": False,
                "files_count": 0,
                "file_names": year_files,
                "financial_data": {},
                "mdna_text": "",
                "parse_errors": year_errors
            })

        if year_errors:
            errors.extend(year_errors)

    return {
        "success": True,
        "company_name": company_name,
        "stock_code": stock_code,
        "total_years": len(year_file_map),
        "total_files": len(files),
        "parsed_years": len([r for r in results if r.get("parsed_success")]),
        "failed_years": len([r for r in results if not r.get("parsed_success")]),
        "results": results,
        "errors": errors if errors else None
    }


@router.post("/financial-files")
async def upload_financial_files(
    files: List[UploadFile] = File(...),
    years: str = Form(...),  # JSON字符串，如 "[2023, 2022, 2021]"
    company_name: str = Form(...),
    stock_code: Optional[str] = Form(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    上传财务文件批量解析（向后兼容 - 每个文件对应一个年份）

    - files: 多个文件
    - years: 每个文件对应的年份，JSON数组格式
    - company_name: 企业名称
    - stock_code: 证券代码（可选）
    """
    try:
        year_list = json.loads(years)
        if len(year_list) != len(files):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="文件数量与年份数量不匹配"
            )
    except json.JSONDecodeError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="年份参数格式错误，应为JSON数组"
        )

    results = []
    errors = []

    for idx, (file, year) in enumerate(zip(files, year_list)):
        # 检查文件类型
        allowed_extensions = ['.pdf', '.xlsx', '.xls', '.docx', '.doc', '.txt', '.csv']
        if not any(file.filename.lower().endswith(ext) for ext in allowed_extensions):
            errors.append(f"文件 {file.filename} 格式不支持")
            continue

        try:
            # 读取文件内容
            content = await file.read()

            # 解析文件
            parse_result = parse_financial_file(
                file_content=content,
                filename=file.filename,
                year=year
            )

            # 添加文件信息
            parse_result["original_filename"] = file.filename
            parse_result["file_size"] = len(content)

            results.append(parse_result)

        except Exception as e:
            errors.append(f"文件 {file.filename} 解析失败: {str(e)}")
            results.append({
                "year": year,
                "filename": file.filename,
                "financial_data": {},
                "mdna_text": "",
                "parsed_success": False,
                "parse_errors": [str(e)]
            })

        finally:
            await file.close()

    return {
        "success": True,
        "company_name": company_name,
        "stock_code": stock_code,
        "total_files": len(files),
        "parsed_files": len([r for r in results if r.get("parsed_success")]),
        "failed_files": len(errors),
        "results": results,
        "errors": errors if errors else None
    }


@router.post("/single-file")
async def upload_single_file(
    file: UploadFile = File(...),
    year: int = Form(...),
    current_user: User = Depends(get_current_user)
):
    """
    上传单个文件并解析

    - file: 单个文件
    - year: 年份
    """
    try:
        content = await file.read()

        result = parse_financial_file(
            file_content=content,
            filename=file.filename,
            year=year
        )

        result["original_filename"] = file.filename
        result["file_size"] = len(content)

        return result

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"文件解析失败: {str(e)}"
        )

    finally:
        await file.close()


@router.post("/parse-preview")
async def parse_preview(
    file: UploadFile = File(...),
    year: int = Form(...),
    current_user: User = Depends(get_current_user)
):
    """
    文件解析预览（不上传保存，仅预览）

    - file: 文件
    - year: 年份
    """
    try:
        content = await file.read()

        result = parse_financial_file(
            file_content=content,
            filename=file.filename,
            year=year
        )

        # 只返回关键信息，减少数据传输
        preview = {
            "year": result["year"],
            "filename": file.filename,
            "parsed_success": result["parsed_success"],
            "financial_data_preview": result["financial_data"],
            "mdna_text_preview": result["mdna_text"][:500] + "..." if len(result["mdna_text"]) > 500 else result["mdna_text"],
            "parse_errors": result.get("parse_errors")
        }

        return preview

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"预览解析失败: {str(e)}"
        )

    finally:
        await file.close()


@router.get("/supported-formats")
def get_supported_formats(
    current_user: User = Depends(get_current_user)
):
    """
    获取支持的文件格式列表
    """
    return {
        "formats": [
            {
                "extension": ".pdf",
                "mime_type": "application/pdf",
                "description": "PDF年报文件（支持财务报告、MD&A等）",
                "parser": "PyMuPDF/pdfplumber"
            },
            {
                "extension": ".xlsx",
                "mime_type": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                "description": "Excel财务表格（结构化数据）",
                "parser": "openpyxl"
            },
            {
                "extension": ".xls",
                "mime_type": "application/vnd.ms-excel",
                "description": "Excel 97-2003财务表格（结构化数据）",
                "parser": "pandas"
            },
            {
                "extension": ".docx",
                "mime_type": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                "description": "Word文档（MD&A文本、管理层讨论等）",
                "parser": "python-docx"
            },
            {
                "extension": ".doc",
                "mime_type": "application/msword",
                "description": "Word 97-2003文档",
                "parser": "antiword"
            },
            {
                "extension": ".txt",
                "mime_type": "text/plain",
                "description": "纯文本文件（MD&A文本）",
                "parser": "直接读取"
            },
            {
                "extension": ".csv",
                "mime_type": "text/csv",
                "description": "CSV财务数据文件",
                "parser": "pandas"
            }
        ],
        "features": {
            "multi_file_per_year": True,
            "max_files_per_year": 10,
            "max_total_files": 50,
            "max_file_size": "50MB"
        }
    }
