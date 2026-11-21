"""MP-11b: the project's storyline as one chain of seven questions.

Each step answers the question the previous step raised. The text is generated from this single source and
injected into the README and guide 00 (identical wording, different link prefix), so the two cannot drift.
It deliberately contains no numbers: every figure lives in a rendered table that the step links to. The claims
below are guarded by tests/test_audit_fixes.py (test_mp11b_*), which fail if the data stops supporting them.
"""

STEPS = (
    ("Can the data be trusted?",
     "Orders, items, payments and reviews are joined at the right grain, and GMV and freight reconcile to the cent between layers, "
     "so no row is multiplied by a join.",
     "03_DATA.md", "Data guide"),
    ("Is \"late\" measured correctly?",
     "A date-level comparison replaces a timestamp comparison that counted same-day afternoon deliveries as late, which removes a "
     "boundary bug and lowers the late rate.",
     "04_METHODOLOGY.md", "Methodology guide"),
    ("Who is responsible for the lateness?",
     "Late deliveries are split into those already late at seller dispatch and those delayed after handover, and the second group is "
     "tested for transit versus promise-setting. Most late deliveries arise after handover and reflect long transit rather than tight "
     "promises; the dataset has no carrier scans, so it cannot say which party causes the long leg.",
     "09_RESULTS_AND_LIMITATIONS.md", "Results guide"),
    ("What does lateness do to customers?",
     "Review timing and a model of what the customer knew at review time show a step-function penalty for a parcel that has not "
     "arrived, not a linear daily decay; repurchase after a late first order is measured directly, and the difference is not "
     "statistically distinguishable from zero.",
     "01_CONCEPTS.md", "Concepts guide"),
    ("How much money is at stake?",
     "Three levels keep what is observed apart from what is assumed: late-order value that was collected, the cost burden, and "
     "illustrative mitigation scenarios with assumed rates. There is no recovered cash, and the repurchase result bounds how much of "
     "the late value can be churn.",
     "04_METHODOLOGY.md", "Methodology guide"),
    ("Where should operations intervene?",
     "Deterministic percentile tiers on seller-caused exposure rank sellers for review, and Pareto concentration lift shows that late "
     "exposure is more concentrated than sales.",
     "08_DESIGN_DECISIONS.md", "Design decisions"),
    ("Does the targeting hold next year?",
     "The same tier rule applied to the first year alone and followed into the next shows partial persistence: part of the excess "
     "carries over and much of it does not, so the tier is a prioritisation list, not proof of a fixed seller trait.",
     "09_RESULTS_AND_LIMITATIONS.md", "Results guide"),
)


def questions():
    return [q for q, _a, _d, _l in STEPS]


def render_storyline(link_prefix=""):
    """Markdown list of the seven steps. link_prefix is "docs/guide/" from the README and "" from inside docs/guide."""
    lines = []
    for i, (question, answer, doc, label) in enumerate(STEPS, start=1):
        if i < len(STEPS):
            hand_off = f" *This raises the next question: {STEPS[i][0]}*"
        else:
            hand_off = " *This closes the chain.*"
        lines.append(f"{i}. **{question}** {answer} ([{label}]({link_prefix}{doc}).){hand_off}")
    return "\n".join(lines)


if __name__ == "__main__":
    print(render_storyline())
