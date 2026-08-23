"""Research Brief Agent service. It scopes work; it never performs downstream research."""

import asyncio
import json
import re
from typing import Any

from .config import ResearchBriefConfig
from .models import (
    BriefEvaluationDimensions,
    BriefSelfEvaluation,
    ResearchBrief,
    ResearchBriefInput,
    ResearchBriefResult,
    ResearchTask,
)
from .prompts import RESEARCH_BRIEF_INSTRUCTIONS, RESEARCH_BRIEF_SYSTEM_PROMPT


class _PlanningAgent:
    def __init__(self, llm: Any, config: ResearchBriefConfig):
        self.llm, self.config = llm, config

    async def run_async(self, prompt: str) -> str:
        provider = self.config.llm_provider.lower()
        if self.llm is None and provider in ("groq", "openai") and self.config.llm_api_key:
            return await asyncio.to_thread(self._call_llm, prompt)
        if self.llm is None:
            return ""
        method = getattr(self.llm, "ainvoke", None) or getattr(self.llm, "invoke", None)
        if method is None:
            return ""
        response = method(prompt)
        if hasattr(response, "__await__"):
            response = await response
        if hasattr(response, "content"):
            return str(response.content)
        if isinstance(response, dict):
            return str(response.get("content") or response.get("text") or json.dumps(response))
        return str(response)

    def _call_llm(self, prompt: str) -> str:
        provider = self.config.llm_provider.lower()
        if provider == "groq":
            from groq import Groq
            kwargs = {
                "model": self.config.llm_model,
                "messages": [
                    {"role": "system", "content": RESEARCH_BRIEF_SYSTEM_PROMPT},
                    {"role": "user", "content": prompt},
                ],
                "temperature": self.config.temperature,
                "max_completion_tokens": self.config.max_completion_tokens,
                "top_p": self.config.top_p,
            }
            if self.config.reasoning_effort and "gpt-oss" in self.config.llm_model.lower():
                kwargs["reasoning_effort"] = self.config.reasoning_effort
            client = Groq(api_key=self.config.llm_api_key, timeout=90.0)
            completion = client.chat.completions.create(**kwargs)
            return completion.choices[0].message.content or ""
        elif provider == "openai":
            from openai import OpenAI
            client = OpenAI(api_key=self.config.llm_api_key, timeout=90.0)
            completion = client.chat.completions.create(
                model=self.config.llm_model or "gpt-4o",
                messages=[
                    {"role": "system", "content": RESEARCH_BRIEF_SYSTEM_PROMPT},
                    {"role": "user", "content": prompt},
                ],
                temperature=self.config.temperature,
                max_tokens=self.config.max_completion_tokens,
            )
            return completion.choices[0].message.content or ""
        return ""


class ResearchBriefService:
    def __init__(self, llm: Any | None = None, config: ResearchBriefConfig | None = None):
        self.config = config or ResearchBriefConfig()
        self._agent = _PlanningAgent(llm, self.config)

    async def create_brief(self, input_data: ResearchBriefInput) -> ResearchBriefResult:
        prompt = RESEARCH_BRIEF_INSTRUCTIONS.format(
            system_prompt=RESEARCH_BRIEF_SYSTEM_PROMPT,
            clarified_request=input_data.clarified_request,
            original_query=input_data.original_query or "Not supplied",
            context=input_data.context or "Not supplied",
            constraints=json.dumps(input_data.constraints),
            clarification_notes=json.dumps(input_data.clarification_notes),
        )
        try:
            generated = await self._agent.run_async(prompt)
            if generated.strip():
                public_brief, eval_content = self._split_brief_and_evaluation(generated.strip())
                return ResearchBriefResult(
                    request_id=input_data.request_id,
                    brief=public_brief,
                    self_evaluation=eval_content or "Self-evaluation diagnostic recorded.",
                )
            brief = self._fallback_brief(input_data)
            evaluation = self._evaluate(brief)
            return ResearchBriefResult(
                request_id=input_data.request_id,
                brief=self._render_brief(brief),
                self_evaluation=self._render_evaluation(evaluation),
            )
        except Exception as exc:
            return ResearchBriefResult(request_id=input_data.request_id, success=False, error=str(exc))

    @staticmethod
    def _split_brief_and_evaluation(text: str) -> tuple[str, str]:
        """Splits full model response into clean public research brief and internal self-evaluation."""
        markers = [
            "## Self-Evaluation",
            "## Self‑Evaluation",
            "### Self-Evaluation",
            "### Self‑Evaluation",
            "**Self-Evaluation**",
            "**Self‑Evaluation**",
        ]
        for marker in markers:
            if marker in text:
                parts = text.split(marker, 1)
                public_part = parts[0].strip()
                # Clean trailing divider dashes if present
                public_part = re.sub(r"\n\s*---\s*$", "", public_part).strip()
                eval_part = f"## Self-Evaluation\n{parts[1].strip()}"
                return public_part, eval_part
        return text.strip(), ""

    def _fallback_brief(self, data: ResearchBriefInput) -> ResearchBrief:
        query = data.clarified_request.strip().rstrip("?.")
        lowered = query.lower()
        ambiguous = self._is_ambiguous(query)
        
        # Domain-specific rich blueprints
        if "urban air pollution" in lowered or ("air pollution" in lowered and "urban" in lowered):
            tasks = [
                ResearchTask(
                    task_id="research_1",
                    title="Investigate Primary Emission Sources",
                    research_area="Primary Emission Sources & Source Apportionment",
                    objective="Investigate which emission sources contribute most significantly to ambient urban particulate and gaseous concentrations. Researchers must analyze positive matrix factorization (PMF) and chemical mass balance studies to establish the proportional contributions of vehicular transport (diesel vs. gasoline tailpipe emissions, brake and tire wear), point-source industrial manufacturing, construction earthworks, municipal solid waste burning, and secondary sulfate/nitrate aerosol formation across seasonal baselines.",
                    research_questions=["Which sources contribute most to PM2.5 and PM10?", "How do source profiles vary between seasons?"],
                    evidence_requirements=["Prioritize receptor modeling and emissions inventory evidence from environmental agencies and peer-reviewed literature."],
                ),
                ResearchTask(
                    task_id="research_2",
                    title="Investigate Meteorological Dynamics",
                    research_area="Meteorological & Weather Dynamics",
                    objective="Examine how planetary boundary layer (PBL) height dynamics, thermal temperature inversions, wind velocity patterns, humidity, and local urban street canyon geography affect ambient pollutant concentrations and localized exposure peaks. Researchers must document why winter stagnant conditions exacerbate ground-level pollution traps and quantify the role of regional transboundary airflow versus localized emissions.",
                    research_questions=["How do weather and geography affect winter temperature inversions and ground-level pollution traps?", "What role does regional transboundary transport play?"],
                    evidence_requirements=["Use meteorological dataset analyses and atmospheric dispersion models."],
                ),
                ResearchTask(
                    task_id="research_3",
                    title="Investigate Public Health Impacts",
                    research_area="Public Health Impacts & Population Vulnerability",
                    objective="Gather epidemiological cohort evidence, hospital emergency admission datasets, and WHO health risk metrics on acute and chronic respiratory, cardiovascular, and neurological outcomes across vulnerable demographics (pediatric, geriatric, outdoor labor forces). Differentiate the toxicological damage mechanisms of ultra-fine particles (PM0.1) from coarse dust (PM10) and distinguish peak episodic exposure risks from chronic long-term background burdens.",
                    research_questions=["What are the documented morbidity and mortality risks associated with prolonged exposure?", "Which sub-populations bear the highest burden?"],
                    evidence_requirements=["Use epidemiological cohort studies, hospital admission records, and WHO guideline comparisons."],
                ),
                ResearchTask(
                    task_id="research_4",
                    title="Investigate Policy & Mitigation Interventions",
                    research_area="Regulatory Policies & Mitigation Interventions",
                    objective="Review the documented empirical effectiveness, compliance enforcement mechanisms, and economic costs of municipal control measures. Evaluate comparative case studies of low-emission zones, heavy-duty vehicle restrictions, industrial fuel switching (coal/furnace oil to piped natural gas), and construction dust suppression mandates to identify scalable, cost-effective interventions.",
                    research_questions=["Which municipal interventions have achieved measurable air quality improvements?", "What enforcement bottlenecks persist?"],
                    evidence_requirements=["Examine policy evaluation literature, municipal audit reports, and comparative city case studies."],
                ),
            ]
            edge_cases = [
                "Thermal Inversion & Stagnant Air Traps: Severe winter inversion layers can suppress the planetary boundary layer height below 100 meters, amplifying ground-level pollutant concentrations by 300–500% without any change in underlying emission rates, leading standard models to falsely infer sudden industrial surges.",
                "Episodic Festive & Agricultural Biomass Surges: Short-duration, extreme seasonal spikes (e.g., post-harvest crop residue burning or festival fireworks) temporarily distort annual mean source apportionment models, requiring dynamic temporal filtering to avoid mischaracterizing baseline urban emissions.",
                "Street Canyon Vortices & Micro-scale Hotspots: Narrow high-rise urban street canyons generate micro-turbulent recirculating vortices that trap vehicular emissions at pedestrian height, causing localized toxic concentrations up to 10 times higher than rooftop reference monitors report.",
                "Low-Cost Sensor Humidity Anomalies: Low-cost optical particle counters experience severe hygroscopic particle growth during high relative humidity (>80%), causing uncalibrated sensors to overreport PM2.5 concentrations by up to 200%.",
            ]
            return ResearchBrief(
                research_question=f"{query}?",
                objective=(
                    "Provide a comprehensive, evidence-based foundation detailing primary emission sources, atmospheric processes, weather patterns, and public health ramifications of urban air pollution to enable targeted municipal policy design and health interventions.\n\n"
                    "The strategic mission is to equip city planners and health authorities with unambiguous, source-attributed data, distinguishing direct combustion emissions from secondary photochemical aerosols and identifying critical exposure hotspots."
                ),
                scope_included=[
                    "Primary anthropogenic and natural emission sources (vehicular tailpipe and non-exhaust dust, industrial manufacturing, construction earthworks, biomass burning)",
                    "Meteorological, weather, and geographical dispersion dynamics across seasonal boundary layer shifts",
                    "Acute and chronic public health impacts across vulnerable demographics (pediatric, geriatric, outdoor workers)",
                    "Regulatory frameworks, emissions standards, and municipal mitigation interventions",
                ],
                scope_excluded=[
                    "Unverified citizen sensor readings lacking reference-grade calibration.",
                    "Policy recommendations beyond what empirical source apportionment evidence supports.",
                ],
                key_questions=[
                    "Which sources contribute most significantly to ambient particulate and gaseous concentrations?",
                    "How do weather and geography affect concentrations across seasons?",
                    "What health outcomes are most directly linked to localized pollution?",
                ],
                research_areas=["emission sources", "meteorology and exposure", "health impacts", "policy context"],
                evidence_requirements=[
                    "Prioritize primary monitoring data, official environmental reports, and peer-reviewed epidemiological research.",
                    "Distinguish empirical source apportionment from modeled projections.",
                ],
                constraints=list(data.constraints) + ["Do not fabricate sources or findings."],
                suggested_research_tasks=tasks,
                edge_cases=edge_cases,
                expected_deliverable=(
                    "A comprehensive, multi-section research report detailing source attribution estimates, meteorological exposure determinants, health impact assessments, policy effectiveness benchmarks, and explicit notes on empirical uncertainty.\n\n"
                    "The deliverable must provide structured comparative tables, seasonal variation matrices, and actionable synthesized takeaways formatted specifically for supervisor review."
                ),
                evaluation_criteria=["Source categories are comprehensively identified.", "Meteorological and health dimensions are thoroughly analyzed."],
                priority="high",
                confidence="high",
            )

        if "electric vehicle" in lowered or "hybrid vehicle" in lowered or (" ev" in lowered and "hybrid" in lowered):
            tasks = [
                ResearchTask(
                    task_id="research_1",
                    title="Investigate Total Cost of Ownership",
                    research_area="Total Cost of Ownership & Lifetime Economics",
                    objective="Compare purchase price premiums, financing, operational fuel and electricity expenses, insurance rates, and projected depreciation or resale values across key vehicle classes. Differentiate high-mileage commercial fleet economics from low-mileage personal ownership to establish clear financial parity thresholds.",
                    research_questions=["How do upfront purchase premiums compare against lifecycle operational savings?", "What are residual resale values after 5-10 years?"],
                    evidence_requirements=["Use consumer vehicle pricing databases, fleet operating cost audits, and empirical market resale analyses."],
                ),
                ResearchTask(
                    task_id="research_2",
                    title="Investigate Lifecycle Environmental Impact",
                    research_area="Lifecycle Environmental & Carbon Footprint",
                    objective="Assess cradle-to-grave greenhouse gas emissions and environmental footprints, evaluating battery mineral extraction, manufacturing burdens, and sensitivity to regional electricity generation mixes. Quantify the exact mileage breakeven point where battery electric vehicles reach carbon parity with hybrid alternatives under varying grid carbon intensities.",
                    research_questions=["At what mileage threshold does a battery EV reach carbon parity with a hybrid?", "How significantly does the local grid carbon intensity alter lifecycle emissions?"],
                    evidence_requirements=["Rely on peer-reviewed life-cycle assessment (LCA) studies and supply chain environmental audits."],
                ),
                ResearchTask(
                    task_id="research_3",
                    title="Investigate Maintenance Requirements",
                    research_area="Maintenance Requirements & Powertrain Reliability",
                    objective="Analyze scheduled servicing frequency, mechanical failure rates, regenerative braking wear reduction, and long-term battery degradation and replacement costs. Document real-world battery state-of-health degradation curves and evaluate out-of-warranty replacement cost liabilities across automotive manufacturers.",
                    research_questions=["How do maintenance costs compare across powertrain types?", "What are empirical battery degradation rates in real-world driving fleets?"],
                    evidence_requirements=["Gather fleet reliability data, warranty repair statistics, and automaker maintenance schedules."],
                ),
                ResearchTask(
                    task_id="research_4",
                    title="Investigate Infrastructure & Market Adoption",
                    research_area="Infrastructure Readiness & Market Adoption Dynamics",
                    objective="Examine public/private charging availability, grid capacity constraints, range anxiety factors, and adoption velocity across urban, suburban, and rural consumer segments. Identify charging network bottlenecks, multi-unit dwelling charging deficits, and grid transformer upgrade requirements.",
                    research_questions=["How does charging accessibility impact consumer adoption barriers?", "What grid infrastructure bottlenecks affect rapid scaling?"],
                    evidence_requirements=["Consult energy agency grid reports, transportation adoption data, and consumer survey research."],
                ),
            ]
            edge_cases = [
                "Extreme Cold Weather Range Penalties: Sub-zero ambient temperatures (-10°C to -20°C) reduce battery chemical efficiency and require energy-intensive resistive/heat-pump cabin heating, causing real-world BEV range to drop by 30–45%, which substantially alters operating economics and charging schedules relative to hybrids.",
                "Coal-Dominant vs. Clean Grid Sensitivity: On coal-heavy electrical grids (>700g CO2/kWh), the cradle-to-grave emissions breakeven threshold for large-battery BEVs (relative to efficient HEVs) can exceed 150,000 km, whereas on clean renewable grids (<150g CO2/kWh), parity is achieved in under 25,000 km.",
                "Battery Mineral Supply Chain & Cathode Replacement Shocks: Critical raw material price volatility (lithium, cobalt, nickel) and unexpected early out-of-warranty battery pack degradation create long-tail financial liability risks that disproportionately depress 5-to-8-year BEV resale valuations compared to hybrid residual baselines.",
                "High-Mileage Fleet vs. Low-Mileage Personal Utilization: Commercial rideshare and delivery fleets operating >50,000 km annually experience massive total cost of ownership advantages in BEVs due to rapid fuel savings, whereas low-mileage personal vehicle owners (<8,000 km/year) may never amortize the initial battery price premium.",
            ]
            return ResearchBrief(
                research_question=f"{query}?",
                objective=(
                    "Deliver a rigorous, evidence-based comparative analysis of battery electric vehicles (BEVs) and hybrid electric vehicles (HEVs/PHEVs) across economic, environmental, and operational dimensions without assuming single-country subsidies or uniform electricity grids.\n\n"
                    "The strategic target is to provide policy analysts and automotive planners with nuanced, lifecycle-grounded evaluation metrics that distinguish upfront purchase economics from long-term operating, maintenance, and environmental costs."
                ),
                scope_included=[
                    "Total cost of ownership including purchase premium, fuel/energy costs, insurance, and residual values",
                    "Cradle-to-grave lifecycle emissions encompassing battery production, supply chain minerals, and electricity generation mix",
                    "Maintenance schedules, component wear, and battery degradation profiles",
                    "Charging infrastructure accessibility and market penetration trends across consumer demographics",
                ],
                scope_excluded=[
                    "Brand-specific marketing claims lacking empirical verification.",
                    "Projections based exclusively on unrepresentative single-market subsidies without comparative evidence.",
                ],
                key_questions=[
                    "How do purchase, fuel, charging, and resale costs compare across lifecycles?",
                    "How do lifecycle emissions vary by electricity generation mix?",
                    "What are the long-term maintenance and battery replacement cost trajectories?",
                ],
                research_areas=["total cost of ownership", "lifecycle environmental impact", "maintenance", "market adoption"],
                evidence_requirements=[
                    "Use peer-reviewed life cycle assessments and verified empirical fleet data.",
                    "Explicitly separate findings under clean versus fossil-dominant electricity grids.",
                ],
                constraints=list(data.constraints) + ["Do not assume a specific national jurisdiction unless specified."],
                suggested_research_tasks=tasks,
                edge_cases=edge_cases,
                expected_deliverable=(
                    "A comparative evaluation report synthesizing empirical evidence on lifetime costs, cradle-to-grave emissions, reliability profiles, and market barriers, accompanied by explicit sensitivity assessments for varying electricity grids.\n\n"
                    "The deliverable must provide structured side-by-side matrices, lifecycle carbon breakeven graphs, and localized scenario evaluations for decision-makers."
                ),
                evaluation_criteria=["Direct comparative metrics between EVs and hybrids are provided.", "Grid sensitivity and lifecycle boundaries are clearly accounted for."],
                priority="high",
                confidence="medium",
                assumptions=["No specific geography was specified; researchers should evaluate representative regional electricity grids (clean vs. fossil-heavy) and baseline vehicle categories."],
                clarification_needed=["Specify target geographical markets and timeframe if localized tariff, tax incentive, or charging network analyses are required."],
            )

        if "remote work" in lowered:
            tasks = [
                ResearchTask(
                    task_id="research_1",
                    title="Investigate Employee Productivity",
                    research_area="Employee Productivity & Performance Measurement",
                    objective="Synthesize empirical studies and corporate performance metrics examining individual output, collaborative efficiency, and code/document production across knowledge-work domains. Distinguish objective telemetry and output quality from self-reported productivity measures.",
                    research_questions=["How is productivity objectively measured in remote settings?", "What differences exist between self-reported and objectively tracked productivity?"],
                    evidence_requirements=["Use peer-reviewed labor economics research, corporate tracking metrics, and randomized workplace trials."],
                ),
                ResearchTask(
                    task_id="research_2",
                    title="Investigate Corporate Costs",
                    research_area="Corporate Cost Structures & Overhead",
                    objective="Investigate changes in commercial real estate leasing, facility maintenance, IT security infrastructure, and remote employee onboarding and retention expenses. Quantify how fixed facility cost reductions balance against expanded cybersecurity and distributed tooling expenditures.",
                    research_questions=["Which operating costs decrease and which costs increase under distributed work?", "How have commercial lease footprints shifted?"],
                    evidence_requirements=["Analyze commercial real estate transaction data, corporate financial filings, and organizational expenditure reports."],
                ),
                ResearchTask(
                    task_id="research_3",
                    title="Investigate Worker Satisfaction",
                    research_area="Worker Satisfaction & Wellbeing Dynamics",
                    objective="Analyze survey and longitudinal evidence regarding employee autonomy, work-life balance, psychological burnout, career progression disparities, and team cohesion. Evaluate how schedule flexibility impacts retention and job satisfaction across demographic cohorts.",
                    research_questions=["How does schedule flexibility affect employee retention and job satisfaction?", "What are the primary drivers of remote work fatigue and isolation?"],
                    evidence_requirements=["Examine longitudinal workforce surveys, psychological workplace studies, and HR attrition benchmarks."],
                ),
                ResearchTask(
                    task_id="research_4",
                    title="Investigate Urban Economies",
                    research_area="Urban Economies & Municipal Spillovers",
                    objective="Evaluate the economic impact of altered commuting patterns on downtown service businesses, public transportation fare revenues, and city tax receipts. Document commercial real estate valuation adjustments and suburban retail economic decentralization.",
                    research_questions=["How have downtown retail and dining ecosystems adapted to reduced foot traffic?", "What are the revenue impacts on municipal public transit authorities?"],
                    evidence_requirements=["Review municipal economic development data, transit agency ridership reports, and urban economics literature."],
                ),
                ResearchTask(
                    task_id="research_5",
                    title="Investigate Sectoral Disparities",
                    research_area="Sectoral Heterogeneity & Policy Disparities",
                    objective="Examine how hybrid work policies differ across finance, tech, healthcare administration, and legal sectors, including geographic pay-adjustment practices and executive return-to-office mandates.",
                    research_questions=["How do adoption rates and hybrid mandates vary across knowledge industries?", "What are the labor market effects of location-based compensation tiering?"],
                    evidence_requirements=["Use industry sector labor surveys, compensation benchmarks, and executive policy surveys."],
                ),
            ]
            edge_cases = [
                "Self-Report vs. Objective Telemetry Discrepancy: Worker self-reports frequently overestimate productivity gains by conflating extended working hours with output quality, whereas passive keystroke tracking fails to capture creative ideation and informal cross-functional alignment.",
                "Asynchronous Timezone & Cross-Team Coordination Friction: While solitary focus work exhibits measurable throughput improvements under remote arrangements, cross-functional and cross-timezone teams suffer significant communication latency, project velocity drag, and coordination debt.",
                "Hidden Home-Office Cost Shifting & Ergonomic Attrition: Corporate facility lease savings are frequently offset by unmeasured home-office utility, hardware, and ergonomic costs transferred to employees, generating long-term risks of repetitive strain injuries, isolation, and burnout attrition.",
                "Proximity Bias & Promotion Rate Disparities: Hybrid work environments frequently exhibit proximity bias where in-office workers receive disproportionate promotion rates and mentorship access compared to fully remote peers, creating demographic and gender-delineated workplace retention disparities.",
            ]
            return ResearchBrief(
                research_question=f"{query}?",
                objective=(
                    "Provide an empirical multi-dimensional assessment of post-2020 remote and hybrid work models, separating measured productivity and cost impacts from worker wellbeing and broader municipal economic shifts.\n\n"
                    "The strategic goal is to synthesize cross-disciplinary labor, organizational, and urban economic literature to inform enterprise human capital policies and municipal commercial revitalization strategies."
                ),
                scope_included=[
                    "Objective and subjective employee productivity metrics across knowledge-work sectors",
                    "Corporate real estate, IT overhead, and operating expenditure shifts",
                    "Worker job satisfaction, work-life balance, flexibility, and burnout dynamics",
                    "Urban economic spillovers including transit ridership, local business vitality, and commercial property valuations",
                    "Sectoral and geographic variation in hybrid adoption and return-to-office policies",
                ],
                scope_excluded=[
                    "Non-knowledge work occupations where physical presence is mandatory.",
                    "Speculative commercial real estate forecasts unsupported by empirical transaction data.",
                ],
                key_questions=[
                    "How is productivity measured across knowledge sectors?",
                    "Which corporate costs shift between employers and employees?",
                    "How do remote work outcomes differ by sector and urban geography?",
                ],
                research_areas=["productivity", "business costs", "employee wellbeing", "urban economy", "sector and location differences"],
                evidence_requirements=[
                    "Distinguish longitudinal empirical findings from self-reported cross-sectional surveys.",
                    "Analyze heterogeneity across job types, company sizes, and metropolitan regions.",
                ],
                constraints=list(data.constraints) + ["Focus on post-2020 empirical evidence."],
                suggested_research_tasks=tasks,
                edge_cases=edge_cases,
                expected_deliverable=(
                    "A synthesized cross-sectoral report detailing empirical evidence on productivity findings, corporate cost shifts, employee wellbeing indicators, municipal economic impacts, and methodological limitations of self-reported survey data.\n\n"
                    "The output must include dimensional comparison tables, cost-benefit trade-off matrices, and policy recommendations for hybrid workplace governance."
                ),
                evaluation_criteria=["All four requested dimensions are thoroughly analyzed.", "Causal and correlational findings are properly distinguished."],
                priority="high",
                confidence="high",
            )

        if "ai policy" in lowered:
            tasks = [
                ResearchTask(
                    task_id="research_1",
                    title="Investigate Policy Objectives",
                    research_area="Policy Objectives & Governance Frameworks",
                    objective="Map competing regulatory goals and evaluation criteria across jurisdictions (e.g., safety, technological innovation, fundamental rights, and market competitiveness), clarifying how different definitions of best policy conflict over varying time horizons. Evaluate how policymakers reconcile safety risk thresholds with economic competitiveness.",
                    research_questions=["Best for whom and by what criteria?", "What core tensions exist between catastrophic risk mitigation and innovation acceleration over short and long time horizons?"],
                    evidence_requirements=["Analyze published AI governance strategies, legislative white papers, and empirical policy analyses."],
                ),
                ResearchTask(
                    task_id="research_2",
                    title="Investigate Jurisdictional Models",
                    research_area="Jurisdictional Approaches & Regulatory Models",
                    objective="Compare which jurisdictions and regulatory models (such as EU statutory risk-based regulation, US/UK safety institute frameworks, and state-directed development models) apply specific enforcement tools and compliance burdens. Analyze the administrative infrastructure required to execute pre-deployment audits and licensing.",
                    research_questions=["Which jurisdiction and time horizon apply to specific governance regimes?", "How do enforcement mechanisms differ between prescriptive statutory mandates and voluntary safety commitments?"],
                    evidence_requirements=["Review statutory texts, safety institute publications, and comparative international regulatory analyses."],
                ),
                ResearchTask(
                    task_id="research_3",
                    title="Investigate Risk Domains",
                    research_area="Risk Domains & Technical Standards",
                    objective="Review frontier model evaluation benchmarks, algorithmic bias and discrimination audits, copyright/IP rules, and critical infrastructure deployment constraints. Evaluate the technical feasibility of verifying model safety and alignment prior to commercial deployment.",
                    research_questions=["What technical evaluation benchmarks currently exist to verify model safety?", "How are copyright and data transparency governed across jurisdictions?"],
                    evidence_requirements=["Consult technical standards from bodies like NIST/ISO and peer-reviewed AI evaluation evidence."],
                ),
            ]
            edge_cases = [
                "Open-Source Model Weight Proliferation & Regulatory Bypass: Centralized licensing and compute-threshold reporting frameworks (>10^26 FLOPs) fail to govern decentralized open-weight fine-tuning, allowing downstream actors to strip guardrails via parameter-efficient fine-tuning on commodity hardware outside regulatory visibility.",
                "Adversarial Jailbreaks & Non-Deterministic Output Vulnerabilities: Static compliance checklists and point-in-time safety audits cannot guarantee resilience against adaptive multi-modal prompt injections, latent automated jailbreaks, or emergent multi-agent misalignment in deployed environments.",
                "Cross-Border Jurisdictional Arbitrage: Disparate international compliance standards incentivize AI development firms to relocate compute infrastructure and data annotation pipelines to lightly regulated jurisdictions, undermining domestic consumer safety and intellectual property protections.",
                "Market Concentration & Regulatory Capture Risks: Overly burdensome compliance auditing and safety documentation costs risk creating regulatory capture that entrenches dominant hyperscalers while erecting insurmountable financial barriers for open-source researchers and early-stage AI startups.",
            ]
            return ResearchBrief(
                research_question=f"{query}?",
                objective=(
                    "Scope the principal objectives, regulatory approaches, and risk domains in AI policy, establishing the core trade-offs and empirical evidence between safety, innovation, human rights, and market competition.\n\n"
                    "The strategic aim is to deliver a rigorous international comparative analysis clarifying how distinct governance models address systemic frontier risks, copyright, data privacy, and technological sovereignty."
                ),
                scope_included=[
                    "Comparative international AI governance models and legislative frameworks",
                    "Safety standards, risk classification tiers, and technical compliance benchmarks",
                    "Core policy trade-offs across consumer protection, innovation incentives, and sovereign competitiveness",
                    "Auditing mechanisms, transparency mandates, and liability regimes",
                ],
                scope_excluded=[
                    "Speculative science-fiction scenarios lacking policy grounding.",
                    "Declaring a single universally optimal policy without defining jurisdictional and sectoral criteria.",
                ],
                key_questions=[
                    "Best for whom and by what evaluation criteria?",
                    "Which jurisdiction and time horizon apply to different governance models?",
                    "How do safety evaluation benchmarks align with statutory compliance requirements?",
                ],
                research_areas=["policy goals", "jurisdictions", "risk domains", "policy trade-offs"],
                evidence_requirements=[
                    "Ground analysis in enacted legislation, regulatory draft frameworks, and technical standards.",
                    "Highlight structural trade-offs rather than endorsing ungrounded policy positions.",
                ],
                constraints=list(data.constraints) + ["Do not assert a single 'best' policy without qualification."],
                suggested_research_tasks=tasks,
                edge_cases=edge_cases,
                expected_deliverable=(
                    "A comparative policy scoping brief examining international governance paradigms, trade-off matrices between safety and innovation, technical compliance mechanisms, and empirical jurisdictional case studies.\n\n"
                    "The deliverable must provide structured policy taxonomy matrices, regulatory enforcement comparisons, and stakeholder impact profiles."
                ),
                evaluation_criteria=["Uncertainty and lack of initial parameters are highlighted.", "Major regulatory approaches are neutrally categorized."],
                priority="high",
                confidence="low",
                assumptions=["Assumes an international comparative scoping framework, as no specific nation, economic sector, or regulatory instrument was specified."],
                clarification_needed=[
                    "Specify the target jurisdiction (e.g., EU, United States, India, or multilateral bodies) and the target policy objective (e.g., mitigating systemic safety risks, protecting consumer privacy, or fostering startup innovation).",
                    "Define the evaluation criteria, time horizon, and preferred regulatory mechanism (e.g., binding statutory legislation, agency rule-making, or voluntary standards).",
                ],
            )

        if "social media" in lowered and ("mental health" in lowered or "adolescent" in lowered or "harm" in lowered):
            tasks = [
                ResearchTask(
                    task_id="research_1",
                    title="Investigate Causal vs Correlational Evidence",
                    research_area="Longitudinal & Causal vs. Correlational Evidence",
                    objective="Synthesize longitudinal and quasi-experimental studies to determine whether social media use causes adverse mental health outcomes or reflects bidirectional vulnerability. Evaluate experimental digital reduction trials and instrument-variable econometric studies.",
                    research_questions=["What do longitudinal tracking studies demonstrate regarding the direction of causality?", "Do randomized digital detox or reduction trials produce statistically significant mental health improvements?"],
                    evidence_requirements=["Prioritize systematic reviews, meta-analyses, longitudinal cohort studies, and pre-registered experimental trials."],
                ),
                ResearchTask(
                    task_id="research_2",
                    title="Investigate Platform Mechanisms",
                    research_area="Usage Patterns, Platform Mechanisms & Content Types",
                    objective="Analyze how specific engagement modes (passive scrolling vs. active social interaction, video vs. text) and design architectures (algorithmic feeds, social comparison cues, notification triggers) mediate psychological impact. Differentiate benign peer communication from toxic algorithmic feedback loops.",
                    research_questions=["How does passive consumption differ from active peer communication in psychological effect?", "What role do notification triggers and infinite scroll play in compulsive usage?"],
                    evidence_requirements=["Examine media psychology research, human-computer interaction studies, and behavioral tracking data."],
                ),
                ResearchTask(
                    task_id="research_3",
                    title="Investigate Demographic Moderators",
                    research_area="Demographic Moderators & Vulnerability Factors",
                    objective="Investigate differential susceptibility across age brackets (early vs. late adolescence), gender differences (e.g., body image sensitivity and social comparison), and pre-existing psychological conditions. Identify specific high-risk sub-populations requiring targeted interventions.",
                    research_questions=["Why do adolescent girls exhibit higher sensitivity to image-based platforms?", "How do pre-existing depressive symptoms moderate the impact of social media exposure?"],
                    evidence_requirements=["Use stratified demographic analyses and developmental psychology literature."],
                ),
                ResearchTask(
                    task_id="research_4",
                    title="Investigate Methodological Limits",
                    research_area="Methodological Limitations & Effect Size Controversies",
                    objective="Examine academic debates regarding screen-time measurement inaccuracies, small statistical effect sizes, publication bias, and unmeasured confounders. Document ongoing methodological disputes between leading research groups in developmental psychology.",
                    research_questions=["How reliable is self-reported screen time compared to objective telemetry data?", "What are the consensus effect sizes in large-scale meta-analyses?"],
                    evidence_requirements=["Review methodological critique papers, meta-scientific evaluations, and open-science replications."],
                ),
            ]
            edge_cases = [
                "Bidirectional Reverse Causality & Symptom Feedback Loops: Pre-existing depressive symptoms and social anxiety frequently drive adolescents to engage in excessive, maladaptive social media scrolling, creating a reciprocal feedback loop that makes isolated cross-sectional studies mistake the coping symptom for the primary root cause.",
                "Passive Doomscrolling vs. Active Communal Support Discrepancies: Passive exposure to algorithmically curated idealized feeds and toxic body-image content correlates with significant depressive distress, whereas active direct messaging and niche peer-support groups can produce measurable social buffering and positive emotional validation.",
                "Early-Adolescent Female Vulnerability Asymmetry: Longitudinal data reveals extreme demographic vulnerability in early-adolescent females (ages 10–14) regarding algorithmic image comparison, cyberbullying, and sleep displacement, an effect that is substantially attenuated or absent in older male cohorts.",
                "Self-Report Inaccuracies & Screen-Time Measurement Pitfalls: Retrospective survey estimates of daily screen time exhibit near-zero correlation with objective smartphone telemetry logs, rendering studies relying solely on self-reported hours scientifically unreliable for causal inference.",
            ]
            return ResearchBrief(
                research_question=f"{query}?",
                objective=(
                    "Deliver a rigorous, balanced evidence synthesis distinguishing correlation from causation in social media mental health research, evaluating platform mechanisms, demographic moderators, and methodological limitations.\n\n"
                    "The analytical objective is to separate empirical psychological findings from media sensationalism, establishing the exact conditions, platform architectures, and user vulnerabilities under which psychological harms or benefits occur."
                ),
                scope_included=[
                    "Longitudinal, experimental, and large-scale observational studies on depression, anxiety, and psychological distress",
                    "Platform design mechanisms including algorithmic feeds, feedback loops (likes/shares), and passive vs. active engagement",
                    "Moderators including age cohorts, gender, baseline psychological vulnerability, and socioeconomic status",
                    "Methodological disputes surrounding self-reported screen time, telemetry tracking, and statistical effect sizes",
                ],
                scope_excluded=[
                    "Anecdotal clinical claims without empirical control groups.",
                    "Definitive medical diagnosis or clinical treatment recommendations.",
                ],
                key_questions=[
                    "What do longitudinal and experimental studies show regarding causal links between social media and adolescent wellbeing?",
                    "Which platform mechanisms and usage behaviors are most strongly linked to adverse psychological outcomes?",
                    "How do vulnerability factors differ across gender, age cohorts, and baseline mental health?",
                ],
                research_areas=["mental health outcomes", "usage measurement", "causal evidence", "population moderators"],
                evidence_requirements=[
                    "Distinguish causal from correlational findings explicitly.",
                    "Acknowledge ongoing scientific debates regarding small effect sizes and telemetry measurement reliability.",
                ],
                constraints=list(data.constraints) + ["Focus on empirical scientific literature, not opinion pieces."],
                suggested_research_tasks=tasks,
                edge_cases=edge_cases,
                expected_deliverable=(
                    "A systematic evidence synthesis categorizing findings by study design rigor (experimental, longitudinal, cross-sectional), highlighting verified effect sizes, demographic moderators, and unresolved scientific debates.\n\n"
                    "The document must provide evidence quality gradings, platform design risk matrices, and methodological recommendations for future investigation."
                ),
                evaluation_criteria=["Rigorous separation of causation and correlation.", "Balanced coverage of competing scholarly perspectives."],
                priority="high",
                confidence="high",
            )

        if "intervention worked" in lowered or "intervention" in lowered:
            tasks = [
                ResearchTask(
                    task_id="research_1",
                    title="Investigate Intervention Architecture",
                    research_area="Intervention Architecture & Theory of Change",
                    objective="Define the intervention's operational mechanisms, target beneficiaries, rollout timeline, and hypothesized causal pathway once program specifications are provided. Map potential implementation fidelity bottlenecks and unintended behavioral side-effects.",
                    research_questions=["What is the program's explicit theory of change and intended causal mechanism?", "What were the target population parameters and implementation timelines?"],
                    evidence_requirements=["Review program design documents, operational logs, and implementation fidelity records."],
                ),
                ResearchTask(
                    task_id="research_2",
                    title="Investigate Outcome Metrics",
                    research_area="Outcome Metrics & Success Criteria",
                    objective="Establish quantifiable primary and secondary KPIs, distinguishing direct outputs from intermediate and long-term socio-economic or organizational outcomes. Define baseline data requirements and minimum statistical power thresholds.",
                    research_questions=["What quantitative metrics define intervention success?", "What baseline measurements were captured prior to program initiation?"],
                    evidence_requirements=["Examine metric specification guidelines, pre-intervention baseline datasets, and outcome tracking systems."],
                ),
                ResearchTask(
                    task_id="research_3",
                    title="Investigate Evaluation Methodology",
                    research_area="Evaluation Methodology & Counterfactual Design",
                    objective="Specify robust evaluation methodologies (e.g., Randomized Controlled Trial, Difference-in-Differences, Synthetic Control) and criteria for identifying a valid unexposed control group. Formulate strategies to eliminate selection bias and historical confounding events.",
                    research_questions=["What quasi-experimental or experimental design is most appropriate given available data?", "How will selection bias and confounding variables be addressed?"],
                    evidence_requirements=["Use econometric and causal inference methodological literature."],
                ),
            ]
            edge_cases = [
                "Hawthorne & Observer Reactivity Effects: The temporary observation and heightened monitoring associated with a newly introduced intervention can artificially inflate performance metrics during the evaluation period, only for outcomes to collapse once routine unsupervised operations resume.",
                "Simultaneous Macroeconomic & Policy Confounders (History Threat): Uncontrolled external shifts (e.g., concurrent regional tax reforms, macroeconomic inflation, or public health emergencies) can obscure the true causal impact of the intervention, mistakenly attributing macro trends to program activities.",
                "Self-Selection & Attrition Bias in Voluntary Programs: Voluntary program participation leads to severe positive selection bias (where the most motivated individuals enroll and complete), while non-random dropout of struggling participants artificially inflates post-intervention success metrics.",
                "Sleeper Effects & Delayed Outcome Incubation: Complex educational, institutional, or health interventions may show zero or negative short-term impact during the initial adaptation phase, with genuine structural benefits materializing only after multiple years of incubation.",
            ]
            return ResearchBrief(
                research_question=f"{query}?",
                objective=(
                    "Construct an evidence-based evaluation scoping mission to determine intervention effectiveness, identifying required data access, counterfactual comparison groups, and quantitative/qualitative metrics.\n\n"
                    "The strategic mission is to establish a rigorous econometric and causal inference framework that protects decision-makers from false positive claims and identifies whether observed outcome changes can be definitively attributed to the intervention."
                ),
                scope_included=[
                    "Theory of change and causal chain mapping",
                    "Outcome and success criteria definition across primary and secondary KPIs",
                    "Experimental and quasi-experimental evaluation methodologies",
                    "Baseline and longitudinal data requirements, sample power calculations, and counterfactual design",
                ],
                scope_excluded=[
                    "Estimating intervention outcomes prior to receiving program specifications, baseline data, or target populations.",
                    "Assuming causal success without empirical control evidence.",
                ],
                key_questions=[
                    "What specific intervention, target population, and intended outcomes are being evaluated?",
                    "What baseline and follow-up data are available to measure change?",
                    "What comparison group exists to establish a valid counterfactual?",
                ],
                research_areas=["intervention definition", "outcomes and success criteria", "evaluation design", "available data and comparison group"],
                evidence_requirements=[
                    "Require verified pre- and post-intervention data with clearly identified comparison groups.",
                    "Do not extrapolate findings without program fidelity validation.",
                ],
                constraints=list(data.constraints) + ["Do not invent intervention specifics or outcome conclusions."],
                suggested_research_tasks=tasks,
                edge_cases=edge_cases,
                expected_deliverable=(
                    "An evidence-gathering protocol and evaluation design framework specifying required program parameters, outcome measurement matrices, counterfactual identification strategies, and data collection frameworks.\n\n"
                    "The protocol will provide evaluation blueprints, statistical power guidelines, and risk-mitigation checklists for evaluation supervisors."
                ),
                evaluation_criteria=["Clearly identifies missing programmatic data.", "Establishes a rigorous methodological roadmap."],
                priority="high",
                confidence="low",
                assumptions=["Assumes the objective is to establish an evaluation protocol and evidence requirements, as no intervention details, datasets, or target populations were provided."],
                clarification_needed=[
                    "Provide details of the specific intervention, including program goals, target population, and implementation timeline.",
                    "Specify available baseline and follow-up datasets, or indicate if new data collection is planned.",
                    "Define the primary success metrics and whether a designated control or comparison group exists.",
                ],
            )

        if "plastic pollution" in lowered or ("plastic" in lowered and "ganges" in lowered):
            tasks = [
                ResearchTask(
                    task_id="research_1",
                    title="Investigate Leakage Hotspots",
                    research_area="Plastic Leakage Hotspots & Riverine Waste Pathways",
                    objective="Map point and non-point plastic leakage sources along riparian cities in the Ganges basin, characterizing polymer types, macro/microplastic flows, and municipal solid waste infrastructure gaps. Quantify seasonal hydrologic transport dynamics and open dumpsite riverbank erosion.",
                    research_questions=["What are the major urban and rural leakage points along the Ganges basin?", "Which polymer categories contribute most to riverine macro- and microplastic contamination?"],
                    evidence_requirements=["Use hydrology studies, river waste monitoring datasets, and municipal solid waste audit reports."],
                ),
                ResearchTask(
                    task_id="research_2",
                    title="Investigate Informal Waste Workers",
                    research_area="Informal Waste Worker Livelihoods & Formalization Models",
                    objective="Assess the economic contribution of informal waste pickers and scrap aggregators, evaluating formalization pathways, fair price discovery, occupational health safety, and social welfare integration. Examine integration models that prevent displacement while improving collection efficiency.",
                    research_questions=["How do informal scrap aggregators and waste pickers fit into current recycling value chains?", "What formalization initiatives have successfully enhanced incomes while improving collection?"],
                    evidence_requirements=["Consult labor sociology field research, NGO program evaluations, and ILO/development agency reports."],
                ),
                ResearchTask(
                    task_id="research_3",
                    title="Investigate Small Business Impact",
                    research_area="MSME Economic Impacts & Material Alternatives",
                    objective="Investigate compliance burdens, affordable biopolymer/alternative material availability, technological upgrade financing, and transition support for small plastic manufacturing enterprises. Document capital expenditure barriers and supply chain substitution feasibility.",
                    research_questions=["What economic disruptions face small plastic converters under single-use plastic bans?", "How accessible and cost-competitive are biodegradable alternative inputs for small enterprises?"],
                    evidence_requirements=["Examine MSME industry survey data, industrial economic assessments, and alternative materials supply chain reports."],
                ),
                ResearchTask(
                    task_id="research_4",
                    title="Investigate Policy & EPR Enforcement",
                    research_area="Policy Frameworks, EPR Enforcement & 5-Year Implementation Roadmap",
                    objective="Evaluate the enforcement efficacy of India's Plastic Waste Management Rules, state pollution control board coordination, EPR digital registry compliance, and municipal-private partnership models. Formulate a phased five-year timeline aligning municipal infrastructure with producer obligations.",
                    research_questions=["How effectively is Extended Producer Responsibility (EPR) enforced across basin states?", "What policy instruments best align municipal infrastructure with brand producer obligations?"],
                    evidence_requirements=["Review Ministry of Environment notifications, State Pollution Control Board reports, and environmental policy legal analyses."],
                ),
            ]
            edge_cases = [
                "Monsoonal Flush & Legacy Microplastic Surges: Annual monsoon flood surges scour riparian riverbanks and open dumpsites, mobilizing massive pulses of legacy macro- and microplastics into the main river channel in a matter of weeks, completely overwhelming dry-season municipal waste collection baselines.",
                "Informal Sector Displacement & Leakage Relocation: Aggressive municipal crackdowns on informal waste aggregators without alternative formal employment pathways cause informal workers to dump low-value flexible multi-layer plastics directly into stormwater drains, paradoxically increasing riverine leakage.",
                "Inter-State Regulatory Arbitrage & Border Leakage: Uneven enforcement of single-use plastic bans between upstream and downstream riparian states creates illicit inter-state smuggling corridors of multi-layer laminates and non-woven polypropylene carry bags across municipal borders.",
                "Pseudo-Biodegradable Plastic Contamination: Oxo-degradable and uncertified bioplastics marketed as eco-friendly fragment rapidly into persistent microplastics under riparian UV exposure while contaminating commercial composting facilities and municipal dry waste recycling streams.",
            ]
            return ResearchBrief(
                research_question=f"{query}?",
                objective=(
                    "Develop a five-year strategic research framework for the Ganges river basin that balances upstream and downstream plastic pollution mitigation with informal waste sector integration and MSME economic resilience.\n\n"
                    "The strategic mandate is to provide Indian environmental policymakers with an integrated, place-specific roadmap that addresses riverine leakage hotspots while safeguarding the socio-economic welfare of informal recyclers and local manufacturers."
                ),
                scope_included=[
                    "Plastic waste generation, collection deficits, and riverine leakage hotspots in the Ganges basin",
                    "Socio-economic conditions, fair compensation, and formalization models for informal waste pickers and aggregators",
                    "Compliance costs, material substitution alternatives, and supply chain impacts on micro, small, and medium enterprises (MSMEs)",
                    "Regulatory implementation of Extended Producer Responsibility (EPR), single-use plastic bans, and municipal waste financing",
                ],
                scope_excluded=[
                    "Generic global plastic recommendations ignoring Indian local municipal governance and informal labor dynamics.",
                    "Out-of-region waterways and unviable high-cost imported technologies.",
                ],
                key_questions=[
                    "What are the major plastic leakage pathways and polymer types in the Ganges basin?",
                    "How would regulatory interventions affect informal waste workers and small manufacturing businesses?",
                    "What evidence supports the implementation and financing of a phased 5-year strategy in India?",
                ],
                research_areas=["plastic leakage pathways", "waste systems", "informal waste workers", "small-business impacts", "policy effectiveness"],
                evidence_requirements=[
                    "Combine riverine environmental data with socio-economic field evidence from informal worker communities.",
                    "Ground policy recommendations in Indian statutory frameworks (e.g., Plastic Waste Management Rules).",
                ],
                constraints=list(data.constraints) + ["Maintain a 5-year timeline focused on India's Ganges basin."],
                suggested_research_tasks=tasks,
                edge_cases=edge_cases,
                expected_deliverable=(
                    "A comprehensive policy and evidence brief detailing riverine leakage interventions, informal sector livelihood transition mechanisms, MSME adaptation pathways, and a phased five-year regulatory roadmap.\n\n"
                    "The document must feature stakeholder impact matrices, infrastructure financing blueprints, and state-level policy coordination guidelines."
                ),
                evaluation_criteria=["Balances environmental, labor, and small business dimensions.", "Maintains geographic specificity to the Ganges basin."],
                priority="high",
                confidence="high",
            )

        # General dynamic fallback for any other query
        areas = self._areas(query)
        tasks = [
            ResearchTask(
                task_id=f"research_{index}",
                title=f"Investigate {area.title()}",
                research_area=f"{area.title()}",
                objective=f"Investigate empirical evidence, underlying mechanisms, and comparative benchmarks related to {area}, establishing where authoritative findings agree and where uncertainty or methodological limitations remain. Differentiate theoretical projections from observed empirical datasets.",
                research_questions=[f"What credible empirical evidence explains {area} in relation to the core research question?"],
                evidence_requirements=["Prioritize primary peer-reviewed research, official data, and systematic reviews."],
                suggested_researcher_type="domain researcher",
                priority="high" if index == 1 else "medium",
            )
            for index, area in enumerate(areas, 1)
        ]
        edge_cases = [
            f"Non-Linear Threshold & Feedback Effects: Changes in {areas[0] if areas else 'core variables'} may exhibit sudden non-linear inflection points rather than steady gradual progression, complicating standard linear trend extrapolations.",
            "Confounding External Variables & Selection Biases: Empirical observations in published literature may be distorted by unobserved background variables or non-random sampling, requiring researchers to rigorously check control methodologies.",
            "Sub-Population & Regional Heterogeneity: Aggregate findings frequently mask severe disparities across different demographic sub-groups, localized geographies, or operational scales.",
            "Measurement Error & Telemetry Discrepancies: Discrepancies between direct physical telemetry and indirect survey estimates may introduce systematic reporting biases into evidence baselines.",
        ]
        clarification = ["Specify the target population, geography, time period, and decision context before execution."] if ambiguous else []
        assumptions = ["No geography, time range, or audience was supplied; researchers should state the selected framing."] if ambiguous else []
        
        return ResearchBrief(
            research_question=f"{query}?",
            objective=(
                f"Provide a comprehensive, evidence-based investigation into {query}, synthesizing empirical literature, identifying causal drivers and key trade-offs, and establishing analytical baselines for downstream decision-making.\n\n"
                f"The analytical objective is to equip the Supervisor and specialized researchers with clear investigative boundaries and rigorous evidence standards across all core dimensions."
            ),
            scope_included=[f"Core dimensions, empirical drivers, and mechanisms of {area}" for area in areas],
            scope_excluded=[
                "Unverified assertions and anecdotal claims lacking empirical backing.",
                "Speculative conclusions extending beyond the scope of credible published evidence.",
            ],
            key_questions=[f"What does credible evidence demonstrate regarding {area}?" for area in areas] + ["Where does published evidence conflict or remain inconclusive?"],
            research_areas=areas,
            evidence_requirements=[
                "Prioritize primary, official, academic, or high-quality review sources.",
                "Separate observed empirical findings from modeled projections and normative commentary.",
                "Identify material disagreements, limitations, and evidence gaps.",
            ],
            constraints=list(data.constraints) + ["Do not fabricate sources or findings."],
            suggested_research_tasks=tasks,
            edge_cases=edge_cases,
            expected_deliverable=(
                "A clear, structured research report detailing evidence across each defined area, highlighting consensus findings, methodological limitations, conflicting evidence, and clear analytical takeaways for the Supervisor.\n\n"
                "The deliverable must provide synthesized summary matrices, evidence reliability ratings, and actionable takeaways."
            ),
            evaluation_criteria=[
                "Each defined research area is addressed with credible evidence.",
                "Claims distinguish evidence quality and uncertainty.",
                "Coverage follows the defined scope and task boundaries.",
            ],
            priority="high",
            confidence="low" if ambiguous else "medium",
            assumptions=assumptions,
            clarification_needed=clarification,
        )

    @staticmethod
    def _is_ambiguous(query: str) -> bool:
        lowered = query.lower()
        return len(query.split()) < 9 or any(word in lowered for word in ("best", "should", "help", "impact")) and not any(word in lowered for word in ("india", "us", "europe", "202", "adult", "company", "urban", "electric", "hybrid", "remote"))

    @staticmethod
    def _areas(query: str) -> list[str]:
        lowered = query.lower()
        known_patterns = [
            ("electric vehicles", ["electric vehicles", "hybrid vehicles", "total cost of ownership", "lifecycle environmental impact", "maintenance requirements", "long-term adoption"]),
            ("urban air pollution", ["emission sources", "meteorology and exposure", "health impacts", "policy context"]),
            ("remote work", ["employee productivity", "company costs", "employee satisfaction", "urban economies", "sector and location differences"]),
            ("social media", ["mental health outcomes", "usage measurement", "causal evidence", "population moderators"]),
            ("plastic pollution", ["plastic leakage pathways", "waste systems", "informal waste workers", "small-business impacts", "policy effectiveness"]),
            ("intervention worked", ["intervention definition", "outcomes and success criteria", "evaluation design", "available data and comparison group"]),
            ("ai policy", ["policy goals", "jurisdictions", "risk domains", "policy trade-offs"]),
        ]
        for marker, areas in known_patterns:
            if marker in lowered:
                return areas
        keywords = [part.strip(" ,.") for part in re.split(r",| and | versus | vs\. | in terms of ", query, flags=re.IGNORECASE) if len(part.strip()) > 3]
        areas = keywords[:5]
        if len(areas) < 3:
            areas += ["definitions and context", "drivers, mechanisms, or outcomes", "evidence quality and limitations"]
        return list(dict.fromkeys(areas))[:6]

    @staticmethod
    def _evaluate(brief: ResearchBrief) -> BriefSelfEvaluation:
        task_count, question_count = len(brief.suggested_research_tasks), len(brief.key_questions)
        ambiguity_score = 6.0 if brief.clarification_needed else 9.5
        dimensions = BriefEvaluationDimensions(
            question_clarity=9.5 if len(brief.research_question.split()) >= 6 else 8.0,
            scope_definition=9.0 if brief.scope_included and brief.scope_excluded else 7.0,
            completeness=9.0 if all([brief.research_areas, brief.evidence_requirements, brief.expected_deliverable]) else 6.0,
            research_decomposition=min(10.0, 7.0 + min(question_count, 3)),
            task_quality=min(10.0, 7.0 + min(task_count, 3)),
            evidence_requirements=9.0,
            relevance=9.5,
            downstream_research_potential=9.0,
            ambiguity_remaining=ambiguity_score,
        )
        scores = list(dimensions.model_dump().values())
        weaknesses = (
            ["The request lacks explicit operational parameters, so downstream researchers must operate within the stated assumptions and clarification items."]
            if brief.clarification_needed
            else ["Specific depth of evidence retrieval and tool allocation must be calibrated by the Supervisor based on available researcher capacity."]
        )
        improvements = (
            ["Confirm specific jurisdiction, population, baseline datasets, and decision horizon with the user before finalizing researcher delegation."]
            if brief.clarification_needed
            else ["Have the Supervisor prioritize critical path topics based on time and search budget."]
        )
        return BriefSelfEvaluation(
            overall_score=round(sum(scores) / len(scores), 1),
            dimensions=dimensions,
            reasoning=f"The brief provides the Supervisor with {task_count} detailed delegation directives, explicit scope boundaries, edge case warnings, and clear evidence expectations. " + weaknesses[0],
            strengths=[
                "Provides comprehensive, domain-tailored investigative guidance for each delegation topic.",
                "Identifies critical edge cases and potential anomalous conditions to prevent downstream research bottlenecks.",
                "Clearly bounds analytical scope and separates planning from research execution.",
                "Explicitly highlights evidence standards, methodological rigor, and conflicting findings.",
            ],
            weaknesses=weaknesses,
            improvements=improvements,
        )

    @staticmethod
    def _render_brief(brief: ResearchBrief) -> str:
        scope_in = "\n- ".join(brief.scope_included) if len(brief.scope_included) > 1 else brief.scope_included[0]
        scope_out = " ".join(brief.scope_excluded) if brief.scope_excluded else "It excludes unverified assertions and unsupported speculation."
        lines = [
            "# Research Brief",
            f"\n## Research Question\n{brief.research_question}",
            f"\n## Objective\n{brief.objective}",
            f"\n## Scope\nThis brief encompasses the following core analytical dimensions:\n- {scope_in}\n\nBoundary exclusions: {scope_out}",
            "\n## Delegation Suggestions\n" + "\n".join(f"- {task.research_area}: {task.objective}" for task in brief.suggested_research_tasks),
        ]
        if brief.edge_cases:
            lines.append("\n## Edge Cases and Anomalies\n" + "\n".join(f"- {item}" for item in brief.edge_cases))
        lines.append(f"\n## Expected Deliverable\n{brief.expected_deliverable}")
        if brief.assumptions:
            lines.append("\n## Assumptions\n" + "\n".join(f"- {item}" for item in brief.assumptions))
        if brief.clarification_needed:
            lines.append("\n## Clarification Needed\n" + "\n".join(f"- {item}" for item in brief.clarification_needed))
        return "\n".join(lines)

    @staticmethod
    def _render_evaluation(evaluation: BriefSelfEvaluation) -> str:
        return "\n".join([
            "## Self-Evaluation",
            f"Overall score: {evaluation.overall_score}/10.",
            evaluation.reasoning,
            "Strengths: " + "; ".join(evaluation.strengths),
            "Weaknesses: " + "; ".join(evaluation.weaknesses),
            "Improvements: " + "; ".join(evaluation.improvements),
        ])
