import json
import os
import boto3

# 🔹 SES 클라이언트 (리전은 본인 SES 리전으로)
SES_REGION = os.environ.get("SES_REGION", "us-west-2")  # 예: 오레곤
ses = boto3.client("ses", region_name=SES_REGION)

# 🔹 간단한 HTML 템플릿 (원하시면 이전에 만든 리포트 템플릿으로 교체 가능)
HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
  <head>
    <meta charset="UTF-8" />
    <title>{subject}</title>
  </head>
  <body style="font-family: Arial, sans-serif;">
    <h2>{title}</h2>
    <p>발송일: {today}</p>

    <h3>📌 오늘의 주요 리포트</h3>
    {reports_html}

    <p style="margin-top:24px;">
      <a href="{portal_url}"
         style="display:inline-block;padding:12px 20px;
                background:#0d6efd;color:#fff;text-decoration:none;
                border-radius:6px;">
        회사 포털 바로가기
      </a>
    </p>

    <hr/>
    <p style="font-size:12px;color:#777;">
      본 메일은 시스템에서 자동 발송되었습니다.<br/>
      문의: {contact_email}
    </p>
  </body>
</html>
"""

def build_reports_html(reports: list) -> str:
    """리포트 리스트를 HTML 블록으로 변환"""
    blocks = []
    for r in reports:
        block = f"""
        <div style="border:1px solid #ddd;border-radius:8px;
                    padding:10px;margin-bottom:10px;background:#fafafa;">
          <div style="font-weight:600;">🔹 {r.get('title', '제목 없음')}</div>
          <div style="font-size:14px;margin:6px 0;">
            {r.get('summary', '요약 없음')}
          </div>
          <a href="{r.get('link', '#')}" target="_blank"
             style="font-size:13px;color:#0d6efd;text-decoration:none;">
            ▶ 자세히 보기
          </a>
        </div>
        """
        blocks.append(block)
    return "\n".join(blocks) if blocks else "<p>오늘 등록된 리포트가 없습니다.</p>"


def lambda_handler(event, context):
    """
    event 예시:
    {
      "from_email": "보내는주소@example.com",
      "to_email": "받는주소@example.com",
      "company_name": "ABC 제조",
      "today": "2025-11-23",
      "portal_url": "https://portal.example.com",
      "contact_email": "safety@example.com",
      "reports": [
        {
          "title": "산안법 제27조 위험성 평가 변경",
          "summary": "위험성 평가 주기가 기존 연 1회에서 반기 1회로 강화되었습니다.",
          "link": "https://law.go.kr/..."
        },
        {
          "title": "중대재해처벌법 시행령 개정",
          "summary": "경영책임자 의무와 안전 예산 확보 의무가 추가되었습니다.",
          "link": "https://law.go.kr/..."
        }
      ]
    }
    """

    # 🔹 테스트용 기본값 (콘솔에서 바로 테스트할 때 event 비어있어도 동작하게)
    if not event:
        event = {}

    company_name = event.get("company_name", "제조업체")
    today = event.get("today", "2025-11-23")
    portal_url = event.get("portal_url", "https://portal.example.com")
    contact_email = event.get("contact_email", "safety@example.com")
    reports = event.get("reports", [])

    from_email = event.get("from_email", os.environ.get("FROM_EMAIL"))
    to_email = event.get("to_email", os.environ.get("TO_EMAIL"))

    if not from_email or not to_email:
        raise ValueError("from_email / to_email 이 설정되어 있지 않습니다. event 또는 환경변수에 넣어주세요.")

    subject = f"{company_name} 데일리 법령 변경 리포트"
    title = f"{company_name} 데일리 리포트"

    reports_html = build_reports_html(reports)

    html_body = HTML_TEMPLATE.format(
        subject=subject,
        title=title,
        today=today,
        reports_html=reports_html,
        portal_url=portal_url,
        contact_email=contact_email,
    )

    # 🔹 SES로 이메일 발송
    response = ses.send_email(
        Source=from_email,  # sandbox라면 Verified 이메일이어야 함
        Destination={
            "ToAddresses": [to_email],  # sandbox에선 여기도 Verified 필요
        },
        Message={
            "Subject": {
                "Data": subject,
                "Charset": "UTF-8",
            },
            "Body": {
                "Html": {
                    "Data": html_body,
                    "Charset": "UTF-8",
                }
            },
        },
    )

    return {
        "statusCode": 200,
        "body": json.dumps({
            "message": "Email sent",
            "messageId": response.get("MessageId")
        })
    }
