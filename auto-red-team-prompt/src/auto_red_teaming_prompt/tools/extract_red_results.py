"""Red Teaming のレポートから情報を抽出する処理"""

import json
from dataclasses import asdict

from auto_red_teaming_prompt.data import ConstitutionInput, RedTeamingResultForBlueTeaming, TargetRisk
from auto_red_teaming_prompt.data.utils import SafetyClassificationQuantitativeStats

MIN_SEVERITY = 0.1


def summarize_vulnerabilities(input_data: ConstitutionInput) -> dict[str, RedTeamingResultForBlueTeaming]:
    """Red Teamingの結果から脆弱性の概要を抽出します。

    Args:
        input_data: Red Teamingの入力データ。

    Returns:
        RedTeamingResultForBlueTeaming: 抽出された脆弱性の概要。

    """

    def _extract_severity(attack_scenario: list[TargetRisk]) -> dict[str, int | float]:
        """攻撃シナリオから重大度を抽出します。

        Args:
            attack_scenario: 攻撃シナリオのリスト。

        Returns:
            dict[str, int]: 攻撃シナリオの名前とその重大度の辞書。

        """
        return {scenario.category: scenario.severity for scenario in attack_scenario}

    raw_results = input_data["red_teaming_results"]
    target_risks = input_data["attack_scenario"]

    severity_dict = _extract_severity(target_risks)
    vulnerability_summary: dict[str, RedTeamingResultForBlueTeaming] = {
        category: RedTeamingResultForBlueTeaming(
            vulnerability_stats=stats,
            severity=severity_dict.get(category, 0),
        )
        for category, stats in raw_results.items()
    }
    return vulnerability_summary


def save_vulnerability_summary(
    summary: dict[str, RedTeamingResultForBlueTeaming],
    output_path: str,
):
    """脆弱性の概要をJSONファイルに保存します。

    Args:
        summary: 脆弱性の概要の辞書。
        output_path: 保存先のファイルパス。

    """
    serializable_summary = {
        category: {
            "vulnerability_stats": asdict(result["vulnerability_stats"]),
            "severity": result["severity"],
        }
        for category, result in summary.items()
    }

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(serializable_summary, f, ensure_ascii=False, indent=4)


def load_vulnerability_summary(summary_file: str) -> dict[str, RedTeamingResultForBlueTeaming]:
    """指定されたファイルから脆弱性の概要を読み込みます。

    Args:
        summary_file: 脆弱性の概要が保存されたJSONファイルのパス。

    Returns:
        dict[str, RedTeamingResultForBlueTeaming]: 読み込まれた脆弱性の概要の辞書。

    """
    with open(summary_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    output = {}
    for category, result in data.items():
        stats = result["vulnerability_stats"]
        vulnerability_stats = SafetyClassificationQuantitativeStats(
            number_of_successes=stats["number_of_successes"],
            number_of_attacks=stats["number_of_attacks"],
            success_rate=stats["success_rate"],
        )
        output[category] = RedTeamingResultForBlueTeaming(
            vulnerability_stats=vulnerability_stats,
            severity=result["severity"],
        )

    return output


def update_with_vulnerability_summary(
    risk_data: list[TargetRisk],
    vulnerability_summary: dict[str, RedTeamingResultForBlueTeaming],
) -> list[TargetRisk]:
    """リスクデータを脆弱性の概要で更新します。

    TargetRisk の severity フィールドについて、max(severity x 攻撃成功率, 0.1)に更新します。
    Args:
        risk_data: リスクデータのリスト。
        vulnerability_summary: 脆弱性の概要の辞書。
    Returns:
        list[TargetRisk]: 更新されたリスクデータのリスト。
    """
    updated_risk_data = []
    for risk in risk_data:
        if risk.category in vulnerability_summary:
            summary = vulnerability_summary[risk.category]
            current_severity = summary["severity"]
            attack_success_rate = summary["vulnerability_stats"].success_rate
            adjusted_severity = max(current_severity * attack_success_rate, MIN_SEVERITY)
            updated_risk = TargetRisk(
                category=risk.category,
                description=risk.description,
                severity=adjusted_severity,
                examples=risk.examples,
            )
            updated_risk_data.append(updated_risk)
        else:
            updated_risk_data.append(risk)
    return updated_risk_data
