"""
Statistical analysis tools for the Stats Agent.

Provides common statistical tests used in medical research:
t-test, chi-square, survival analysis, and sample size calculation.
"""

import logging
import math
from typing import Any, Optional

from pydantic import BaseModel, Field

logger = logging.getLogger("medical_paper_agent")


class TTestInput(BaseModel):
    group1: list[float] = Field(description="Data for group 1")
    group2: list[float] = Field(description="Data for group 2")
    paired: bool = Field(default=False, description="Whether to use paired t-test")


class ChiSquareInput(BaseModel):
    observed: list[list[int]] = Field(description="Contingency table as 2D array")


class SurvivalInput(BaseModel):
    times: list[float] = Field(description="Survival/event times")
    events: list[int] = Field(description="Event indicators (1=event, 0=censored)")
    groups: Optional[list[int]] = Field(
        default=None, description="Group labels for comparison"
    )


class SampleSizeInput(BaseModel):
    effect_size: float = Field(
        description="Expected effect size (Cohen's d or proportion difference)"
    )
    alpha: float = Field(default=0.05, description="Significance level")
    power: float = Field(default=0.80, description="Statistical power")
    test_type: str = Field(default="two_sample_ttest", description="Type of test")


def run_ttest(
    group1: list[float], group2: list[float], paired: bool = False
) -> dict[str, Any]:
    """
    Run an independent or paired t-test.

    Returns test statistic, p-value, confidence interval, and effect size.
    """
    try:
        from scipy import stats
        import numpy as np

        g1 = np.array(group1)
        g2 = np.array(group2)

        if paired:
            stat, p_value = stats.ttest_rel(g1, g2)
            diff = g1 - g2
            effect_size = float(np.mean(diff) / np.std(diff, ddof=1))
        else:
            stat, p_value = stats.ttest_ind(g1, g2)
            pooled_std = math.sqrt(
                (
                    (len(g1) - 1) * np.var(g1, ddof=1)
                    + (len(g2) - 1) * np.var(g2, ddof=1)
                )
                / (len(g1) + len(g2) - 2)
            )
            effect_size = (
                float((np.mean(g1) - np.mean(g2)) / pooled_std)
                if pooled_std > 0
                else 0.0
            )

        # Confidence interval for mean difference
        mean_diff = float(np.mean(g1) - np.mean(g2))
        se = float(np.sqrt(np.var(g1, ddof=1) / len(g1) + np.var(g2, ddof=1) / len(g2)))
        ci_low = mean_diff - 1.96 * se
        ci_high = mean_diff + 1.96 * se

        return {
            "test_name": "paired_ttest" if paired else "independent_ttest",
            "statistic": float(stat),
            "p_value": float(p_value),
            "confidence_interval": (round(ci_low, 4), round(ci_high, 4)),
            "effect_size": round(effect_size, 4),
            "mean_group1": round(float(np.mean(g1)), 4),
            "mean_group2": round(float(np.mean(g2)), 4),
            "n_group1": len(g1),
            "n_group2": len(g2),
            "interpretation": _interpret_p_value(float(p_value)),
        }

    except ImportError:
        return {"error": "scipy not available", "test_name": "ttest"}
    except Exception as e:
        return {"error": str(e), "test_name": "ttest"}


def run_chi_square(observed: list[list[int]]) -> dict[str, Any]:
    """
    Run a chi-square test of independence on a contingency table.
    """
    try:
        from scipy import stats
        import numpy as np

        table = np.array(observed)
        chi2, p_value, dof, expected = stats.chi2_contingency(table)

        # Cramér's V for effect size
        n = table.sum()
        min_dim = min(table.shape) - 1
        cramers_v = math.sqrt(chi2 / (n * min_dim)) if min_dim > 0 and n > 0 else 0.0

        return {
            "test_name": "chi_square",
            "statistic": round(float(chi2), 4),
            "p_value": round(float(p_value), 6),
            "degrees_of_freedom": int(dof),
            "effect_size": round(cramers_v, 4),
            "expected": expected.tolist(),
            "interpretation": _interpret_p_value(float(p_value)),
        }

    except ImportError:
        return {"error": "scipy not available", "test_name": "chi_square"}
    except Exception as e:
        return {"error": str(e), "test_name": "chi_square"}


def run_survival_analysis(
    times: list[float],
    events: list[int],
    groups: Optional[list[int]] = None,
) -> dict[str, Any]:
    """
    Run Kaplan-Meier survival analysis with optional log-rank test for group comparison.
    """
    try:
        from scipy import stats
        import numpy as np

        times_arr = np.array(times)
        events_arr = np.array(events)

        # Basic summary statistics
        result: dict[str, Any] = {
            "test_name": "survival_analysis",
            "n_subjects": len(times),
            "n_events": int(events_arr.sum()),
            "median_time": (
                round(float(np.median(times_arr[events_arr == 1])), 2)
                if events_arr.sum() > 0
                else None
            ),
        }

        if groups is not None:
            groups_arr = np.array(groups)
            unique_groups = np.unique(groups_arr)

            if len(unique_groups) == 2:
                # Log-rank test approximation
                g0 = groups_arr == unique_groups[0]
                g1 = groups_arr == unique_groups[1]

                events_g0 = int(events_arr[g0].sum())
                events_g1 = int(events_arr[g1].sum())
                n0 = int(g0.sum())
                n1 = int(g1.sum())

                # Simplified log-rank statistic
                expected_g0 = (events_g0 + events_g1) * n0 / (n0 + n1)
                expected_g1 = (events_g0 + events_g1) * n1 / (n0 + n1)

                if expected_g0 > 0 and expected_g1 > 0:
                    chi2 = (events_g0 - expected_g0) ** 2 / expected_g0 + (
                        events_g1 - expected_g1
                    ) ** 2 / expected_g1
                    p_value = float(1 - stats.chi2.cdf(chi2, df=1))
                else:
                    chi2 = 0.0
                    p_value = 1.0

                result["log_rank_statistic"] = round(chi2, 4)
                result["p_value"] = round(p_value, 6)
                result["interpretation"] = _interpret_p_value(p_value)
                result["group_summary"] = {
                    str(unique_groups[0]): {"n": n0, "events": events_g0},
                    str(unique_groups[1]): {"n": n1, "events": events_g1},
                }

        return result

    except ImportError:
        return {"error": "scipy not available", "test_name": "survival_analysis"}
    except Exception as e:
        return {"error": str(e), "test_name": "survival_analysis"}


def calculate_sample_size(
    effect_size: float,
    alpha: float = 0.05,
    power: float = 0.80,
    test_type: str = "two_sample_ttest",
) -> dict[str, Any]:
    """
    Calculate required sample size for a given effect size, alpha, and power.

    Uses normal approximation for common test types.
    """
    try:
        from scipy import stats

        z_alpha = stats.norm.ppf(1 - alpha / 2)
        z_beta = stats.norm.ppf(power)

        if test_type == "two_sample_ttest":
            # n per group for two-sample t-test
            n_per_group = math.ceil(2 * ((z_alpha + z_beta) / effect_size) ** 2)
            return {
                "test_type": test_type,
                "n_per_group": n_per_group,
                "total_n": n_per_group * 2,
                "effect_size": effect_size,
                "alpha": alpha,
                "power": power,
            }

        elif test_type == "chi_square":
            # Simplified sample size for chi-square
            n = math.ceil(((z_alpha + z_beta) / effect_size) ** 2)
            return {
                "test_type": test_type,
                "total_n": n,
                "effect_size": effect_size,
                "alpha": alpha,
                "power": power,
            }

        else:
            return {"error": f"Unsupported test type: {test_type}"}

    except ImportError:
        return {"error": "scipy not available"}
    except Exception as e:
        return {"error": str(e)}


def generate_stats_report(results: list[dict[str, Any]]) -> dict[str, Any]:
    """Generate a summary statistics report from multiple analysis results."""
    report = {
        "total_analyses": len(results),
        "significant_results": 0,
        "analyses": results,
    }

    for r in results:
        p = r.get("p_value")
        if p is not None and p < 0.05:
            report["significant_results"] += 1

    return report


def _interpret_p_value(p_value: float) -> str:
    """Provide a standard interpretation of p-value."""
    if p_value < 0.001:
        return "Highly significant (p < 0.001)"
    elif p_value < 0.01:
        return "Very significant (p < 0.01)"
    elif p_value < 0.05:
        return "Significant (p < 0.05)"
    elif p_value < 0.10:
        return "Marginally significant (0.05 ≤ p < 0.10)"
    else:
        return "Not significant (p ≥ 0.10)"
