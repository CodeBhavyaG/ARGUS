import os
import sys
import re
from pathlib import Path
from langchain.messages import HumanMessage
import json
from dotenv import load_dotenv
from langchain.agents import create_agent
from langchain.messages import SystemMessage
from langchain_groq import ChatGroq

project_root = Path(__file__).resolve().parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from state import SupervisorState

load_dotenv()
api_key = os.getenv("api_key") or os.getenv("GROQ_API_KEY")

def get_llm(api_key: str | None = None, model_name: str = "qwen/qwen3.6-27b", temperature: float = 0.1) -> ChatGroq | None:
    """Initialize and return the Groq Chat model."""
    key = api_key or os.getenv("api_key") or os.getenv("GROQ_API_KEY")
    if not key or key in ("your_groq_api_key_here", "api_key_value"):
        return None
    return ChatGroq(
        model_name=model_name,
        api_key=key,
        temperature=temperature,
        reasoning_effort="none",
        reasoning_format="parsed",
    )

def get_system_prompt() -> str:
    """Load the Supervisor system prompt from prompt/Superviser.md."""
    prompt_path = project_root / "prompt" / "Superviser.md"
    return prompt_path.read_text(encoding="utf-8")

def create_supervisor_agent(llm_model=None):
    """Create a structured Supervisor Agent instance."""
    if llm_model is None:
        llm_model = get_llm()
    if llm_model is None:
        raise ValueError("Cannot create supervisor agent: Groq API key is not configured.")
    system_prompt = get_system_prompt()
    return create_agent(
        model=llm_model,
        tools=[],
        system_prompt=SystemMessage(system_prompt),
        response_format=SupervisorState,
    )

_default_agent = None

def get_default_agent():
    global _default_agent
    if _default_agent is None:
        llm_model = get_llm()
        if llm_model is not None:
            _default_agent = create_supervisor_agent(llm_model)
    return _default_agent

def run_supervisor(brief: str, supervisor_agent=None) -> SupervisorState:
    """
    Invoke the supervisor agent on a given research brief and return SupervisorState.
    """
    clean_brief = re.sub(r'<think>.*?</think>', '', brief, flags=re.DOTALL).strip()
    header_match = re.search(r'(#*\s*1\.\s*Research Question.*|#*\s*Research Brief.*|##*\s*Research Question.*)', clean_brief, flags=re.DOTALL | re.IGNORECASE)
    if header_match:
        clean_brief = header_match.group(1).strip()

    # If mock agent is passed (e.g., in unit tests)
    if supervisor_agent is not None:
        message = [HumanMessage(clean_brief)]
        result = supervisor_agent.invoke({"messages": message})
        if isinstance(result, dict) and "structured_response" in result:
            return result["structured_response"]
        if isinstance(result, SupervisorState):
            return result

    llm_model = get_llm()
    if llm_model is None:
        raise ValueError("Groq API key not configured. Set GROQ_API_KEY in .env or pass a mock supervisor_agent.")

    system_prompt = get_system_prompt()
    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=clean_brief[:4000]),
    ]

    try:
        structured_llm = llm_model.with_structured_output(SupervisorState)
        res = structured_llm.invoke(messages)
        if isinstance(res, SupervisorState):
            return res
        elif isinstance(res, dict):
            return SupervisorState(**res)
    except Exception:
        pass

    try:
        agent = get_default_agent()
        if agent is not None:
            result = agent.invoke({"messages": [HumanMessage(clean_brief[:4000])]})
            if "structured_response" in result:
                return result["structured_response"]
    except Exception:
        pass

    # Direct JSON prompt fallback
    json_instructions = (
        f"{system_prompt}\n\n"
        f"Deconstruct the following Research Brief into balanced tasks across ResearchAgent_1, ResearchAgent_2, and ResearchAgent_3.\n\n"
        f"Brief:\n{clean_brief[:3000]}\n\n"
        "Output ONLY a valid JSON object matching: "
        '{"research_brief": "...", "tasks": [{"task_id": "task_1", "task_description": "...", "assigned_agent": "ResearchAgent_1", "status": "pending", "result": null}]}'
    )
    raw_resp = llm_model.invoke([HumanMessage(content=json_instructions)])
    raw_text = raw_resp.content if hasattr(raw_resp, "content") else str(raw_resp)
    json_match = re.search(r'\{.*\}', raw_text, flags=re.DOTALL)
    if json_match:
        data = json.loads(json_match.group(0))
        return SupervisorState(**data)
    raise ValueError(f"Could not parse supervisor output from: {raw_text[:200]}")

if __name__ == "__main__":
    message = [
        HumanMessage("""# Research Brief

## Research Question
What are the major causes of urban air pollution?

## Objective
Provide a comprehensive, evidence-based foundation detailing primary emission sources, atmospheric processes, weather patterns, and public health ramifications of urban air pollution to enable targeted municipal policy design and health interventions.

The strategic mission is to equip city planners and health authorities with unambiguous, source-attributed data, distinguishing direct combustion emissions from secondary photochemical aerosols and identifying critical exposure hotspots.

## Scope
This brief encompasses the following core analytical dimensions:
- Primary anthropogenic and natural emission sources (vehicular tailpipe and non-exhaust dust, industrial manufacturing, construction earthworks, biomass burning)
- Meteorological, weather, and geographical dispersion dynamics across seasonal boundary layer shifts
- Acute and chronic public health impacts across vulnerable demographics (pediatric, geriatric, outdoor workers)
- Regulatory frameworks, emissions standards, and municipal mitigation interventions

Boundary exclusions: Unverified citizen sensor readings lacking reference-grade calibration. Policy recommendations beyond what empirical source apportionment evidence supports.

## Delegation Suggestions
- Primary Emission Sources & Source Apportionment: Investigate which emission sources contribute most significantly to ambient urban particulate and gaseous concentrations. Researchers must analyze positive matrix factorization (PMF) and chemical mass balance studies to establish the proportional contributions of vehicular transport (diesel vs. gasoline tailpipe emissions, brake and tire wear), point-source industrial manufacturing, construction earthworks, municipal solid waste burning, and secondary sulfate/nitrate aerosol formation across seasonal baselines.
- Meteorological & Weather Dynamics: Examine how planetary boundary layer (PBL) height dynamics, thermal temperature inversions, wind velocity patterns, humidity, and local urban street canyon geography affect ambient pollutant concentrations and localized exposure peaks. Researchers must document why winter stagnant conditions exacerbate ground-level pollution traps and quantify the role of regional transboundary airflow versus localized emissions.
- Public Health Impacts & Population Vulnerability: Gather epidemiological cohort evidence, hospital emergency admission datasets, and WHO health risk metrics on acute and chronic respiratory, cardiovascular, and neurological outcomes across vulnerable demographics (pediatric, geriatric, outdoor labor forces). Differentiate the toxicological damage mechanisms of ultra-fine particles (PM0.1) from coarse dust (PM10) and distinguish peak episodic exposure risks from chronic long-term background burdens.
- Regulatory Policies & Mitigation Interventions: Review the documented empirical effectiveness, compliance enforcement mechanisms, and economic costs of municipal control measures. Evaluate comparative case studies of low-emission zones, heavy-duty vehicle restrictions, industrial fuel switching (coal/furnace oil to piped natural gas), and construction dust suppression mandates to identify scalable, cost-effective interventions.

## Edge Cases and Anomalies
- Thermal Inversion & Stagnant Air Traps: Severe winter inversion layers can suppress the planetary boundary layer height below 100 meters, amplifying ground-level pollutant concentrations by 300–500% without any change in underlying emission rates, leading standard models to falsely infer sudden industrial surges.
- Episodic Festive & Agricultural Biomass Surges: Short-duration, extreme seasonal spikes (e.g., post-harvest crop residue burning or festival fireworks) temporarily distort annual mean source apportionment models, requiring dynamic temporal filtering to avoid mischaracterizing baseline urban emissions.
- Street Canyon Vortices & Micro-scale Hotspots: Narrow high-rise urban street canyons generate micro-turbulent recirculating vortices that trap vehicular emissions at pedestrian height, causing localized toxic concentrations up to 10 times higher than rooftop reference monitors report.
- Low-Cost Sensor Humidity Anomalies: Low-cost optical particle counters experience severe hygroscopic particle growth during high relative humidity (>80%), causing uncalibrated sensors to overreport PM2.5 concentrations by up to 200%.

## Expected Deliverable
A comprehensive, multi-section research report detailing source attribution estimates, meteorological exposure determinants, health impact assessments, policy effectiveness benchmarks, and explicit notes on empirical uncertainty.

The deliverable must provide structured comparative tables, seasonal variation matrices, and actionable synthesized takeaways formatted specifically for supervisor review.

## Self-Evaluation
Overall score: 9.4/10.
The brief provides the Supervisor with 4 detailed delegation directives, explicit scope boundaries, edge case warnings, and clear evidence expectations. Specific depth of evidence retrieval and tool allocation must be calibrated by the Supervisor based on available researcher capacity.
Strengths: Provides comprehensive, domain-tailored investigative guidance for each delegation topic.; Identifies critical edge cases and potential anomalous conditions to prevent downstream research bottlenecks.; Clearly bounds analytical scope and separates planning from research execution.; Explicitly highlights evidence standards, methodological rigor, and conflicting findings.
Weaknesses: Specific depth of evidence retrieval and tool allocation must be calibrated by the Supervisor based on available researcher capacity.
Improvements: Have the Supervisor prioritize critical path topics based on time and search budget.""")
    ]

    result = agent.invoke({"messages": message})
    all_results = [result["structured_response"].model_dump()]
    print(json.dumps(all_results, indent=2))