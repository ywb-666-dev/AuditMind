"""
财务报表勾稽关系校验服务
增强版：支持7种核心勾稽关系校验
"""
from typing import Dict, List, Any


class StatementValidator:
    """财务报表勾稽关系校验器"""

    def validate(self, statement_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        执行完整的勾稽关系校验
        """
        errors = []
        warnings = []
        details = {}

        bs = statement_data.get('balance_sheet', {})
        inc = statement_data.get('income_statement', {})
        cf = statement_data.get('cash_flow', {})
        eq = statement_data.get('equity_change', {})

        # 1. 资产负债表平衡校验
        self._validate_balance_sheet_equilibrium(bs, errors, warnings, details)

        # 2. 利润表链式校验
        self._validate_income_statement_chain(inc, errors, warnings, details)

        # 3. 现金流量表连续性校验
        self._validate_cash_flow_continuity(cf, errors, warnings, details)

        # 4. 资产负债表与利润表勾稽
        self._validate_bs_income_linkage(bs, inc, eq, errors, warnings, details)

        # 5. 资产负债表与现金流量表勾稽
        self._validate_bs_cashflow_linkage(bs, cf, errors, warnings, details)

        # 6. 所有者权益变动表与资产负债表勾稽
        self._validate_equity_bs_linkage(bs, eq, errors, warnings, details)

        # 7. 现金流量表间接法校验
        self._validate_cashflow_indirect(cf, inc, errors, warnings, details)

        is_valid = len(errors) == 0
        validation_score = self._calculate_validation_score(errors, warnings)

        return {
            "is_valid": is_valid,
            "errors": errors,
            "warnings": warnings,
            "details": details,
            "validation_score": validation_score,
        }

    def _get_item_value(self, data: Dict, item_name: str, field: str = "ending_balance") -> float:
        """从报表数据中获取指定项目的值"""
        if not isinstance(data, dict):
            return 0.0
        for section, items in data.items():
            if isinstance(items, list):
                for item in items:
                    if isinstance(item, dict) and item.get("item_name") == item_name:
                        val = item.get(field)
                        if val is not None:
                            try:
                                return float(val)
                            except (ValueError, TypeError):
                                return 0.0
        return 0.0

    def _sum_section(self, data: Dict, section_name: str, field: str = "ending_balance") -> float:
        """计算某个分类下的总和"""
        if not isinstance(data, dict):
            return 0.0
        items = data.get(section_name, [])
        if not isinstance(items, list):
            return 0.0
        total = 0.0
        for item in items:
            if isinstance(item, dict):
                val = item.get(field)
                if val is not None:
                    try:
                        # 跳过"小计""合计"等汇总行，避免重复计算
                        name = item.get("item_name", "")
                        if any(kw in name for kw in ["小计", "合计", "总计", "净额"]):
                            continue
                        total += float(val)
                    except (ValueError, TypeError):
                        pass
        return total

    def _validate_balance_sheet_equilibrium(self, bs, errors, warnings, details):
        """1. 资产负债表平衡: 资产 = 负债 + 所有者权益"""
        if not bs:
            warnings.append("资产负债表数据为空，无法校验平衡性")
            return

        # 计算各类资产
        current_assets = self._sum_section(bs, "流动资产")
        non_current_assets = self._sum_section(bs, "非流动资产")
        total_assets = current_assets + non_current_assets

        # 计算各类负债
        current_liabilities = self._sum_section(bs, "流动负债")
        non_current_liabilities = self._sum_section(bs, "非流动负债")
        total_liabilities = current_liabilities + non_current_liabilities

        # 计算所有者权益
        total_equity = self._sum_section(bs, "所有者权益")

        details["balance_sheet"] = {
            "total_assets": total_assets,
            "current_assets": current_assets,
            "non_current_assets": non_current_assets,
            "total_liabilities": total_liabilities,
            "current_liabilities": current_liabilities,
            "non_current_liabilities": non_current_liabilities,
            "total_equity": total_equity,
        }

        diff = abs(total_assets - (total_liabilities + total_equity))
        if diff > 0.01:
            errors.append(
                f"资产负债表不平衡：资产总计({total_assets:,.2f}) ≠ 负债合计({total_liabilities:,.2f}) + 所有者权益({total_equity:,.2f})，差额: {diff:,.2f}"
            )

        # 检查资产结构
        if total_assets > 0:
            current_ratio = current_assets / total_assets
            if current_ratio > 0.9:
                warnings.append(f"流动资产占比过高({current_ratio*100:.1f}%)，请检查非流动资产是否遗漏")
            elif current_ratio < 0.1:
                warnings.append(f"流动资产占比过低({current_ratio*100:.1f}%)，请核实")

    def _validate_income_statement_chain(self, inc, errors, warnings, details):
        """2. 利润表链式校验: 营业利润 → 利润总额 → 净利润"""
        if not inc:
            warnings.append("利润表数据为空，无法校验链式关系")
            return

        revenue = self._get_item_value(inc, "营业收入", "current_period")
        operating_profit = self._get_item_value(inc, "营业利润", "current_period")
        total_profit = self._get_item_value(inc, "利润总额", "current_period")
        income_tax = self._get_item_value(inc, "所得税费用", "current_period")
        net_profit = self._get_item_value(inc, "净利润", "current_period")

        details["income_statement"] = {
            "revenue": revenue,
            "operating_profit": operating_profit,
            "total_profit": total_profit,
            "income_tax": income_tax,
            "net_profit": net_profit,
        }

        # 校验：利润总额 ≈ 营业利润 + 营业外收入 - 营业外支出
        non_operating_income = self._get_item_value(inc, "营业外收入", "current_period")
        non_operating_expense = self._get_item_value(inc, "营业外支出", "current_period")
        expected_total = operating_profit + non_operating_income - non_operating_expense

        if operating_profit != 0 and total_profit != 0:
            diff = abs(total_profit - expected_total)
            if diff > 0.01:
                warnings.append(
                    f"利润总额({total_profit:,.2f})与营业利润+营业外收支({expected_total:,.2f})不一致，差额: {diff:,.2f}"
                )

        # 校验：净利润 = 利润总额 - 所得税费用
        if total_profit != 0 and net_profit != 0:
            expected_net = total_profit - income_tax
            diff = abs(net_profit - expected_net)
            if diff > 0.01:
                errors.append(
                    f"净利润({net_profit:,.2f}) ≠ 利润总额({total_profit:,.2f}) - 所得税费用({income_tax:,.2f})，差额: {diff:,.2f}"
                )

        # 校验：净利润 < 利润总额（所得税应为正）
        if net_profit > total_profit and total_profit > 0:
            warnings.append("净利润大于利润总额，请检查所得税费用是否为负值")

        # 校验：营业收入 > 0
        if revenue <= 0:
            warnings.append("营业收入为0或负数，请核实")

    def _validate_cash_flow_continuity(self, cf, errors, warnings, details):
        """3. 现金流量表连续性: 期末 = 期初 + 净增加额"""
        if not cf:
            warnings.append("现金流量表数据为空，无法校验连续性")
            return

        beginning = self._get_item_value(cf, "期初现金及现金等价物余额", "current_period")
        net_increase = self._get_item_value(cf, "现金及现金等价物净增加额", "current_period")
        ending = self._get_item_value(cf, "期末现金及现金等价物余额", "current_period")

        details["cash_flow"] = {
            "beginning_balance": beginning,
            "net_increase": net_increase,
            "ending_balance": ending,
        }

        if beginning != 0 or ending != 0:
            expected_ending = beginning + net_increase
            diff = abs(ending - expected_ending)
            if diff > 0.01:
                errors.append(
                    f"现金流量表不连续：期末余额({ending:,.2f}) ≠ 期初({beginning:,.2f}) + 净增加额({net_increase:,.2f})，差额: {diff:,.2f}"
                )

        # 校验：经营活动+投资+筹资 = 净增加额
        operating = self._get_item_value(cf, "经营活动产生的现金流量净额", "current_period")
        investing = self._get_item_value(cf, "投资活动产生的现金流量净额", "current_period")
        financing = self._get_item_value(cf, "筹资活动产生的现金流量净额", "current_period")
        exchange = self._get_item_value(cf, "汇率变动对现金的影响", "current_period")

        expected_net = operating + investing + financing + exchange
        if abs(net_increase - expected_net) > 0.01 and net_increase != 0:
            warnings.append(
                f"现金净增加额({net_increase:,.2f})与三类活动合计({expected_net:,.2f})不一致"
            )

    def _validate_bs_income_linkage(self, bs, inc, eq, errors, warnings, details):
        """4. 资产负债表与利润表勾稽: 未分配利润"""
        if not bs or not inc:
            return

        # 未分配利润期末 = 期初 + 净利润 - 分配
        retained_earnings_end = self._get_item_value(bs, "未分配利润", "ending_balance")
        retained_earnings_beg = self._get_item_value(bs, "未分配利润", "beginning_balance")
        net_profit = self._get_item_value(inc, "净利润", "current_period")

        details["bs_income_linkage"] = {
            "retained_earnings_beginning": retained_earnings_beg,
            "retained_earnings_ending": retained_earnings_end,
            "net_profit": net_profit,
        }

        if retained_earnings_beg != 0 or net_profit != 0:
            # 简化校验：期末未分配利润 ≈ 期初 + 净利润
            expected = retained_earnings_beg + net_profit
            diff = abs(retained_earnings_end - expected)
            if diff > 0.01:
                warnings.append(
                    f"未分配利润期末({retained_earnings_end:,.2f})与期初+净利润({expected:,.2f})差异较大({diff:,.2f})，"
                    f"可能本期进行了利润分配"
                )

    def _validate_bs_cashflow_linkage(self, bs, cf, errors, warnings, details):
        """5. 资产负债表与现金流量表勾稽: 货币资金"""
        if not bs or not cf:
            return

        cash_bs = self._get_item_value(bs, "货币资金", "ending_balance")
        cash_cf = self._get_item_value(cf, "期末现金及现金等价物余额", "current_period")

        details["bs_cashflow_linkage"] = {
            "cash_from_balance_sheet": cash_bs,
            "cash_from_cash_flow": cash_cf,
        }

        if cash_bs != 0 and cash_cf != 0:
            diff = abs(cash_bs - cash_cf)
            if diff > 0.01:
                warnings.append(
                    f"资产负债表货币资金({cash_bs:,.2f})与现金流量表期末现金({cash_cf:,.2f})不一致，"
                    f"差额: {diff:,.2f}（可能包含受限资金）"
                )

    def _validate_equity_bs_linkage(self, bs, eq, errors, warnings, details):
        """6. 所有者权益变动表与资产负债表勾稽"""
        if not bs or not eq:
            return

        # 校验各权益科目是否一致
        equity_items = ["实收资本（或股本）", "资本公积", "盈余公积", "未分配利润"]
        mismatches = []

        for item_name in equity_items:
            bs_end = self._get_item_value(bs, item_name, "ending_balance")
            eq_end = self._get_item_value(eq, item_name, "ending_balance")

            if bs_end != 0 and eq_end != 0:
                diff = abs(bs_end - eq_end)
                if diff > 0.01:
                    mismatches.append(f"{item_name}: 资产负债表({bs_end:,.2f}) ≠ 权益变动表({eq_end:,.2f})")

        if mismatches:
            warnings.append("所有者权益变动表与资产负债表不一致：" + "；".join(mismatches))

        details["equity_bs_linkage"] = {"mismatches": mismatches}

    def _validate_cashflow_indirect(self, cf, inc, errors, warnings, details):
        """7. 现金流量表间接法校验 (经营现金流与净利润关系)"""
        if not cf or not inc:
            return

        operating_cf = self._get_item_value(cf, "经营活动产生的现金流量净额", "current_period")
        net_profit = self._get_item_value(inc, "净利润", "current_period")

        details["cashflow_indirect"] = {
            "operating_cash_flow": operating_cf,
            "net_profit": net_profit,
        }

        if net_profit != 0:
            ratio = operating_cf / net_profit if net_profit != 0 else 0

            if ratio < 0:
                warnings.append(
                    f"经营活动现金流量净额({operating_cf:,.2f})为负，"
                    f"而净利润({net_profit:,.2f})为正，可能存在大量应收账款或存货积压"
                )
            elif ratio < 0.5:
                warnings.append(
                    f"经营现金流/净利润比率过低({ratio:.2f})，"
                    f"利润质量可能较差，建议关注现金流与利润的差异原因"
                )
            elif ratio > 3:
                warnings.append(
                    f"经营现金流/净利润比率过高({ratio:.2f})，"
                    f"可能存在大额预收款项或非经常性现金流入"
                )

    def _calculate_validation_score(self, errors: List[str], warnings: List[str]) -> float:
        """计算校验得分 (0-100)"""
        base_score = 100.0
        # 每个错误扣15分
        base_score -= len(errors) * 15
        # 每个警告扣5分
        base_score -= len(warnings) * 5
        return max(0.0, min(100.0, base_score))
