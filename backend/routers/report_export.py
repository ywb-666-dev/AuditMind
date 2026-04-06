"""
报告导出路由 - 支持PDF、Word、Excel多种格式
"""
from fastapi import APIRouter, Depends, HTTPException, status, Response
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from typing import Optional

from backend.core.database import get_db
from backend.core.security import get_current_user
from backend.models.database import User, DetectionRecord, Report
from backend.services.enhanced_report_service import enhanced_report_service
from backend.services.professional_report_service import generate_professional_report

router = APIRouter(prefix="/report", tags=["报告导出"])


@router.post("/{detection_id}/export")
def export_report(
    detection_id: int,
    format: str = "pdf",
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    导出检测报告（支持 pdf, word, excel）

    Args:
        detection_id: 检测记录ID
        format: 导出格式 (pdf, word, excel)
    """
    # 获取检测记录
    detection = db.query(DetectionRecord).filter(
        DetectionRecord.id == detection_id,
        DetectionRecord.user_id == current_user.id
    ).first()

    if not detection:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="检测记录不存在"
        )

    # 检查会员权限
    if current_user.membership_level == "free" and format != "pdf":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="免费用户仅支持PDF导出，请升级会员以使用Word/Excel导出"
        )

    try:
        # 生成报告文件
        result = enhanced_report_service.generate_report_file(
            detection=detection,
            report_type=format,
            user=current_user
        )

        # 创建或更新报告记录
        report = db.query(Report).filter(
            Report.record_id == detection_id,
            Report.report_type == format
        ).first()

        if not report:
            report = Report(
                record_id=detection_id,
                report_type=format,
                file_path=result["file_path"],
                file_url=f"/api/report/{detection_id}/download?format={format}"
            )
            db.add(report)
        else:
            report.file_path = result["file_path"]
            report.download_count = 0

        db.commit()

        return {
            "success": True,
            "message": f"{format.upper()}报告生成成功",
            "report_id": report.id,
            "filename": result["filename"],
            "file_type": result["file_type"],
            "file_size": result["file_size"],
            "download_url": f"/report/{detection_id}/download?format={format}"
        }

    except RuntimeError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"报告生成失败: {str(e)}"
        )


@router.get("/{detection_id}/download")
def download_report_file(
    detection_id: int,
    format: str = "pdf",
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    下载报告文件

    Args:
        detection_id: 检测记录ID
        format: 文件格式 (pdf, word, excel)
    """
    # 获取检测记录
    detection = db.query(DetectionRecord).filter(
        DetectionRecord.id == detection_id,
        DetectionRecord.user_id == current_user.id
    ).first()

    if not detection:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="检测记录不存在"
        )

    # 检查会员权限（如果是非PDF格式）
    if current_user.membership_level == "free" and format != "pdf":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="免费用户仅支持PDF导出，请升级会员以使用Word/Excel导出"
        )

    # 查找报告记录
    report = db.query(Report).filter(
        Report.record_id == detection_id,
        Report.report_type == format
    ).first()

    if not report:
        # 如果报告不存在，实时生成
        try:
            result = enhanced_report_service.generate_report_file(
                detection=detection,
                report_type=format,
                user=current_user
            )
            file_path = result["file_path"]
            filename = result["filename"]
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"报告生成失败: {str(e)}"
            )
    else:
        file_path = report.file_path
        filename = report.file_path.split("/")[-1]

        # 增加下载次数
        report.download_count += 1
        db.commit()

    # 检查文件是否存在
    import os
    if not os.path.exists(file_path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="报告文件不存在，请重新生成"
        )

    # 设置MIME类型
    media_type_map = {
        "pdf": "application/pdf",
        "word": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "excel": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    }
    media_type = media_type_map.get(format, "application/octet-stream")

    # 确保文件存在且可读
    if not os.path.exists(file_path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="报告文件不存在"
        )

    # FileResponse会自动处理Content-Disposition
    # 注意：filename如果包含中文，应该使用RFC 5987编码
    # 这里我们依赖FileResponse自动处理

    return FileResponse(
        path=file_path,
        filename=filename,
        media_type=media_type
    )


@router.get("/{detection_id}/export-formats")
def get_export_formats(
    detection_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    获取可用的导出格式列表
    """
    formats = [
        {
            "id": "pdf",
            "name": "PDF报告",
            "description": "专业排版，适合打印和分享",
            "icon": "📄",
            "available": True,
            "requires_membership": False
        },
        {
            "id": "word",
            "name": "Word文档",
            "description": "可编辑格式，适合二次加工",
            "icon": "📝",
            "available": current_user.membership_level != "free",
            "requires_membership": True
        },
        {
            "id": "excel",
            "name": "Excel数据",
            "description": "结构化数据，适合深度分析",
            "icon": "📊",
            "available": current_user.membership_level != "free",
            "requires_membership": True
        }
    ]

    return {
        "formats": formats,
        "current_membership": current_user.membership_level
    }
