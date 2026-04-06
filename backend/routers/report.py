"""
检测报告路由
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
import uuid
from datetime import datetime, timedelta

from backend.core.database import get_db
from backend.core.security import get_current_user
from backend.models.database import User, DetectionRecord, Report
from backend.schemas.schemas import ReportResponse

router = APIRouter(prefix="/report", tags=["报告管理"])


def generate_share_token() -> str:
    """
    生成分享令牌
    """
    return uuid.uuid4().hex


@router.get("/list", response_model=List[ReportResponse])
def get_report_list(
    page: int = 1,
    page_size: int = 10,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    获取报告列表
    """
    # 查询当前用户的所有检测记录ID
    detection_ids = [d.id for d in db.query(DetectionRecord).filter(
        DetectionRecord.user_id == current_user.id
    ).all()]

    # 查询关联的报告
    query = db.query(Report).filter(
        Report.record_id.in_(detection_ids)
    ).order_by(Report.created_at.desc())

    offset = (page - 1) * page_size
    reports = query.offset(offset).limit(page_size).all()

    return reports


@router.get("/{report_id}", response_model=ReportResponse)
def get_report(
    report_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    获取报告详情
    """
    report = db.query(Report).join(Report.detection).filter(
        Report.id == report_id,
        DetectionRecord.user_id == current_user.id
    ).first()

    if not report:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="报告不存在"
        )

    # 增加查看次数
    report.view_count += 1
    db.commit()

    return report


@router.post("/{detection_id}/generate")
def generate_report(
    detection_id: int,
    report_type: str = "basic",
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    生成检测报告
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

    # 检查是否已有报告
    existing_report = db.query(Report).filter(
        Report.record_id == detection_id
    ).first()

    if existing_report:
        return existing_report

    # 创建报告记录
    db_report = Report(
        record_id=detection_id,
        report_type=report_type,
        file_path=f"/reports/{detection_id}_{report_type}.pdf",
        file_url=f"/api/report/{detection_id}/download"
    )

    db.add(db_report)
    db.commit()
    db.refresh(db_report)

    # TODO: 实际生成 PDF 报告
    # 这里仅创建记录，实际 PDF 生成需要额外的报告生成服务

    return db_report


@router.post("/{report_id}/share")
def share_report(
    report_id: int,
    expire_days: int = 7,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    分享报告（生成分享链接）
    """
    report = db.query(Report).join(Report.detection).filter(
        Report.id == report_id,
        DetectionRecord.user_id == current_user.id
    ).first()

    if not report:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="报告不存在"
        )

    # 生成分享令牌
    share_token = generate_share_token()
    report.share_token = share_token
    report.is_public = True
    report.share_expire_at = datetime.utcnow() + timedelta(days=expire_days)

    db.commit()

    return {
        "share_token": share_token,
        "share_url": f"/report/share/{share_token}",
        "expire_at": report.share_expire_at
    }


@router.post("/{report_id}/unshare")
def unshare_report(
    report_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    取消分享报告
    """
    report = db.query(Report).join(Report.detection).filter(
        Report.id == report_id,
        DetectionRecord.user_id == current_user.id
    ).first()

    if not report:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="报告不存在"
        )

    report.is_public = False
    report.share_token = None
    report.share_expire_at = None

    db.commit()

    return {"message": "已取消分享"}


@router.get("/share/{share_token}")
def get_shared_report(
    share_token: str,
    db: Session = Depends(get_db)
):
    """
    通过分享令牌查看报告
    """
    report = db.query(Report).filter(
        Report.share_token == share_token,
        Report.is_public == True
    ).first()

    if not report:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="分享链接无效或已过期"
        )

    # 检查是否过期
    if report.share_expire_at and report.share_expire_at < datetime.utcnow():
        raise HTTPException(
            status_code=status.HTTP_410_GONE,
            detail="分享链接已过期"
        )

    # 增加查看次数
    report.view_count += 1
    db.commit()

    return report


@router.delete("/{report_id}")
def delete_report(
    report_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    删除报告
    """
    report = db.query(Report).join(Report.detection).filter(
        Report.id == report_id,
        DetectionRecord.user_id == current_user.id
    ).first()

    if not report:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="报告不存在"
        )

    db.delete(report)
    db.commit()

    return {"message": "删除成功"}
