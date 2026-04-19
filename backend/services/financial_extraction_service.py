"""
财务数据AI提取服务
从上传的文件中自动提取并结构化四表一注数据
"""
import json
import re
import httpx
from typing import Dict, List, Optional, Any
from datetime import datetime

from backend.core.config import settings

# ==================== AI Prompt 模板 ====================

EXTRACTION_PROMPT_TEMPLATE = """你是一位资深财务分析师，擅长从企业年报和财务报表中提取结构化数据。

【任务】
从以下财务报告文本和表格数据中，提取并结构化"四表一注"数据。
报告年度：{report_year}
企业名称：{company_name}

【已解析的文本内容】
{merged_text}

【已提取的表格数据】
{merged_tables}

【输出要求】
请严格按照以下JSON格式输出，不要包含任何其他说明文字：

{{
    "balance_sheet": {{
        "流动资产": [
            {{"item_name": "货币资金", "item_code": "1001", "ending_balance": null, "beginning_balance": null, "notes": null}}
        ],
        "非流动资产": [],
        "流动负债": [],
        "非流动负债": [],
        "所有者权益": []
    }},
    "income_statement": {{
        "营业收入": [],
        "营业成本及费用": [],
        "利润相关": []
    }},
    "cash_flow": {{
        "经营活动": [],
        "投资活动": [],
        "筹资活动": [],
        "现金及等价物": []
    }},
    "equity_change": {{
        "所有者权益变动": []
    }},
    "notes": "## 一、公司基本情况\\n（请根据文本填写）\\n## 二、财务报表编制基础\\n...",
    "extraction_metadata": {{
        "confidence": 0.00,
        "source_pages": [],
        "missing_items": [],
        "currency_unit": "元"
    }}
}}

【重要规则】
1. 所有金额统一转换为"元"（如果原文是万元，乘以10000；如果是亿元，乘以100000000）
2. 如果某项数据在原文中确实不存在，设为 null，不要编造
3. item_code 使用标准会计科目代码，如不确定可省略
4. notes 字段可填写该项的特殊说明或数据来源
5. 请尽可能多地提取数据，不要遗漏

【标准项目名称对照】
资产负债表项目：货币资金、交易性金融资产、应收票据、应收账款、预付款项、其他应收款、存货、一年内到期的非流动资产、其他流动资产、可供出售金融资产、持有至到期投资、长期股权投资、投资性房地产、固定资产、在建工程、无形资产、开发支出、商誉、长期待摊费用、递延所得税资产、其他非流动资产、短期借款、交易性金融负债、应付票据、应付账款、预收款项、应付职工薪酬、应交税费、应付利息、应付股利、其他应付款、一年内到期的非流动负债、其他流动负债、长期借款、应付债券、长期应付款、预计负债、递延收益、递延所得税负债、其他非流动负债、实收资本（或股本）、资本公积、盈余公积、未分配利润

利润表项目：营业收入、其中：主营业务收入、其他业务收入、营业成本、税金及附加、销售费用、管理费用、研发费用、财务费用、其他收益、投资收益、公允价值变动收益、信用减值损失、资产减值损失、资产处置收益、营业利润、营业外收入、营业外支出、利润总额、所得税费用、净利润

现金流量表项目：销售商品、提供劳务收到的现金、收到的税费返还、收到其他与经营活动有关的现金、经营活动现金流入小计、购买商品、接受劳务支付的现金、支付给职工以及为职工支付的现金、支付的各项税费、支付其他与经营活动有关的现金、经营活动现金流出小计、经营活动产生的现金流量净额、收回投资收到的现金、取得投资收益收到的现金、处置固定资产等收回的现金、投资活动现金流入小计、购建固定资产等支付的现金、投资支付的现金、投资活动现金流出小计、投资活动产生的现金流量净额、吸收投资收到的现金、取得借款收到的现金、筹资活动现金流入小计、偿还债务支付的现金、分配股利、利润或偿付利息支付的现金、筹资活动现金流出小计、筹资活动产生的现金流量净额、汇率变动对现金的影响、现金及现金等价物净增加额、期初现金及现金等价物余额、期末现金及现金等价物余额

所有者权益变动表项目：实收资本（或股本）、资本公积、盈余公积、未分配利润、所有者权益合计
"""

GAP_FILL_PROMPT_TEMPLATE = """你是一位资深财务分析师。以下是从企业年报中提取的部分财务数据，部分项目缺失或不确定。

【已知数据】
{known_data}

【缺失项目】
{missing_items}

【上下文文本】
{context_text}

【任务】
基于已知数据和上下文，对缺失项目进行合理估计。对于每个估计值：
1. 给出估计数值（金额统一为元）
2. 说明估计依据和推理过程
3. 给出置信度（0-1）
4. 如果完全无法估计，confidence设为0，estimated_value设为null

【输出格式】
{{
    "filled_items": [
        {{
            "item_name": "项目名称",
            "statement_type": "balance_sheet|income_statement|cash_flow|equity_change",
            "estimated_value": 123456.78,
            "reasoning": "基于...计算得出",
            "confidence": 0.75,
            "calculation_method": "公式推导|行业均值|比例估算|无法估计"
        }}
    ],
    "warnings": ["估计项1的置信度较低，建议核实"]
}}
"""


# ==================== 核心提取服务 ====================

class FinancialDataExtractor:
    """财务数据AI提取器"""

    def __init__(self):
        self.model = settings.MODEL_QWEN
        self.base_url = settings.DASHSCOPE_BASE_URL
        self.api_key = settings.DASHSCOPE_API_KEY

    async def extract_from_parsed_files(
        self,
        parsed_results: List[Dict[str, Any]],
        company_name: str,
        report_year: int,
        fill_missing: bool = True,
    ) -> Dict[str, Any]:
        """
        从已解析的文件中提取结构化四表一注数据
        """
        # 1. 合并所有文本和表格数据
        merged_text = self._merge_text_content(parsed_results)
        merged_tables = self._extract_all_tables(parsed_results)

        # 2. 构建AI提示词
        prompt = EXTRACTION_PROMPT_TEMPLATE.format(
            merged_text=merged_text[:8000] if merged_text else "无文本内容",
            merged_tables=json.dumps(merged_tables, ensure_ascii=False, indent=2)[:4000] if merged_tables else "无表格数据",
            company_name=company_name,
            report_year=report_year,
        )

        # 3. 调用LLM
        response = await self._call_llm(prompt, max_tokens=4000)

        # 4. 解析结果
        structured_data = self._parse_extraction_response(response)

        # 5. 收集缺失项
        missing_items = self._collect_missing_items(structured_data)
        structured_data["extraction_metadata"]["missing_items"] = missing_items

        # 6. 可选：AI补全缺失项
        ai_filled = []
        if fill_missing and missing_items:
            ai_filled = await self._fill_missing_items(
                structured_data, missing_items, merged_text
            )
            structured_data["ai_filled_items"] = ai_filled
            # 将AI估计值填入数据结构
            self._apply_filled_items(structured_data, ai_filled)
        else:
            structured_data["ai_filled_items"] = []

        return structured_data

    def _merge_text_content(self, parsed_results: List[Dict]) -> str:
        """合并所有文本内容"""
        texts = []
        for result in parsed_results:
            if isinstance(result, dict):
                # 从 FileParser 的结果中提取文本
                text = result.get("text", "")
                mdna = result.get("mdna_text", "")
                if text:
                    texts.append(text)
                if mdna:
                    texts.append(f"\n[MD&A部分]\n{mdna}")
        return "\n\n".join(texts)

    def _extract_all_tables(self, parsed_results: List[Dict]) -> List[Dict]:
        """提取所有表格数据"""
        tables = []
        for result in parsed_results:
            if isinstance(result, dict):
                # 提取财务数据表格
                financial_data = result.get("financial_data", {})
                if financial_data:
                    tables.append(financial_data)
                # 提取DataFrame格式的表格
                df_data = result.get("dataframes", [])
                if df_data:
                    tables.extend(df_data)
        return tables

    async def _call_llm(self, prompt: str, max_tokens: int = 2000, temperature: float = 0.3) -> str:
        """调用 LLM API"""
        try:
            async with httpx.AsyncClient(timeout=120.0) as client:
                response = await client.post(
                    f"{self.base_url}/chat/completions",
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": self.model,
                        "messages": [
                            {"role": "system", "content": "你是财务数据分析专家，擅长从企业年报和财务报表中提取结构化数据。请严格按照要求的JSON格式输出。"},
                            {"role": "user", "content": prompt}
                        ],
                        "temperature": temperature,
                        "max_tokens": max_tokens,
                    }
                )

                if response.status_code == 200:
                    result = response.json()
                    content = result["choices"][0]["message"]["content"]
                    return content
                else:
                    print(f"⚠️ LLM API调用失败: {response.status_code} - {response.text}")
                    return ""

        except Exception as e:
            print(f"⚠️ LLM API异常: {e}")
            return ""

    def _parse_extraction_response(self, response: str) -> Dict[str, Any]:
        """解析 LLM 提取响应 """
        if not response:
            return self._get_empty_result()

        try:
            # 清理响应数据，移除markdown代码块标记
            cleaned = re.sub(r'^```json\s*|\s*```$', '', response.strip(), flags=re.MULTILINE)
            cleaned = cleaned.strip()

            data = json.loads(cleaned)

            # 确保必要字段存在
            result = {
                "balance_sheet": data.get("balance_sheet", {}),
                "income_statement": data.get("income_statement", {}),
                "cash_flow": data.get("cash_flow", {}),
                "equity_change": data.get("equity_change", {}),
                "notes": data.get("notes", ""),
                "extraction_metadata": data.get("extraction_metadata", {
                    "confidence": 0.0,
                    "source_pages": [],
                    "missing_items": [],
                    "currency_unit": "元"
                }),
                "ai_filled_items": [],
            }
            return result

        except json.JSONDecodeError as e:
            print(f"⚠️ JSON解析失败: {e}")
            # 尝试从文本中提取JSON
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                try:
                    return json.loads(json_match.group())
                except:
                    pass
            return self._get_empty_result()

    def _get_empty_result(self) -> Dict[str, Any]:
        """获取空结果结构"""
        return {
            "balance_sheet": {},
            "income_statement": {},
            "cash_flow": {},
            "equity_change": {},
            "notes": "",
            "extraction_metadata": {
                "confidence": 0.0,
                "source_pages": [],
                "missing_items": ["所有项目"],
                "currency_unit": "元"
            },
            "ai_filled_items": [],
        }

    def _collect_missing_items(self, data: Dict[str, Any]) -> List[str]:
        """收集所有值为null或缺失的项目"""
        missing = []
        for stmt_type in ["balance_sheet", "income_statement", "cash_flow", "equity_change"]:
            stmt_data = data.get(stmt_type, {})
            for section, items in stmt_data.items():
                if isinstance(items, list):
                    for item in items:
                        if isinstance(item, dict):
                            # 检查关键字段是否为null
                            has_value = any(
                                item.get(k) is not None
                                for k in ["ending_balance", "beginning_balance", "current_period", "previous_period", "increase", "decrease"]
                            )
                            if not has_value:
                                missing.append(f"{stmt_type}.{section}.{item.get('item_name', '未知')}")
        return missing

    async def _fill_missing_items(
        self,
        structured_data: Dict[str, Any],
        missing_items: List[str],
        context_text: str,
    ) -> List[Dict[str, Any]]:
        """使用AI补全缺失项"""
        if not missing_items:
            return []

        # 构建已知数据摘要（避免Prompt过长）
        known_summary = {}
        for stmt_type in ["balance_sheet", "income_statement", "cash_flow", "equity_change"]:
            stmt_data = structured_data.get(stmt_type, {})
            known_summary[stmt_type] = {}
            for section, items in stmt_data.items():
                if isinstance(items, list):
                    for item in items:
                        if isinstance(item, dict):
                            for k in ["ending_balance", "beginning_balance", "current_period", "previous_period"]:
                                if item.get(k) is not None:
                                    known_summary[stmt_type][item.get("item_name", "")] = item[k]

        prompt = GAP_FILL_PROMPT_TEMPLATE.format(
            known_data=json.dumps(known_summary, ensure_ascii=False, indent=2)[:2000],
            missing_items=json.dumps(missing_items[:50], ensure_ascii=False),  # 最多50个
            context_text=context_text[:2000] if context_text else "无上下文",
        )

        response = await self._call_llm(prompt, max_tokens=2000, temperature=0.2)

        if not response:
            return []

        try:
            cleaned = re.sub(r'^```json\s*|\s*```$', '', response.strip(), flags=re.MULTILINE)
            data = json.loads(cleaned)
            return data.get("filled_items", [])
        except Exception as e:
            print(f"⚠️ 补全结果解析失败: {e}")
            return []

    def _apply_filled_items(self, structured_data: Dict[str, Any], filled_items: List[Dict]):
        """将AI填充的值应用到数据结构中"""
        for fill in filled_items:
            stmt_type = fill.get("statement_type")
            item_name = fill.get("item_name")
            value = fill.get("estimated_value")

            if not stmt_type or not item_name or value is None:
                continue

            stmt_data = structured_data.get(stmt_type, {})
            for section, items in stmt_data.items():
                if isinstance(items, list):
                    for item in items:
                        if isinstance(item, dict) and item.get("item_name") == item_name:
                            # 根据报表类型填入对应字段
                            if stmt_type == "balance_sheet":
                                item["ending_balance"] = value
                            elif stmt_type in ["income_statement", "cash_flow"]:
                                item["current_period"] = value
                            elif stmt_type == "equity_change":
                                item["ending_balance"] = value
