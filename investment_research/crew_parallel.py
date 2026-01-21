"""Enhanced Investment Research Crew with Red/Blue Team Architecture and Parallel Execution."""

import os
import concurrent.futures
from pathlib import Path
from typing import Dict, List, Tuple

import yaml
from crewai import Agent, Crew, Process, Task
from crewai_tools import ScrapeWebsiteTool

from .tools import (
    investment_data_tool,
    price_sentiment_data_tool,
    governance_data_tool,
    business_profile_tool,
    key_metrics_tool,
    sec_filings_tool,
    web_search_tool,
    historical_multiples_tool,
    peer_comparison_tool,
    valuation_chart_tool,
)
from .progress_callbacks import create_task_callback


class ParallelInvestmentResearchCrew:
    """Red/Blue Team Investment Research Crew with parallel execution."""

    def __init__(self):
        """Initialize the crew with Red/Blue team configuration."""
        self.config_dir = Path(__file__).parent / "config"
        self.agents_config = self._load_yaml("agents.yaml")
        self.tasks_config = self._load_yaml("tasks.yaml")
        self.scrape_tool = ScrapeWebsiteTool()

    def _load_yaml(self, filename: str) -> dict:
        """Load a YAML configuration file."""
        path = self.config_dir / filename
        with open(path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f)

    def _create_agent(
        self,
        agent_key: str,
        team_perspective: str = "neutral",
        tools: List = None
    ) -> Agent:
        """
        Create an agent with optional team perspective modification.

        Args:
            agent_key: Key in agents.yaml
            team_perspective: 'blue' (optimistic), 'red' (skeptical), or 'neutral'
            tools: List of tools for the agent
        """
        cfg = self.agents_config[agent_key]

        # Modify backstory based on team perspective
        backstory = cfg["backstory"]
        if team_perspective == "blue":
            backstory += "\n\nTEAM PERSPECTIVE: You are part of the BLUE TEAM (Bull Case). Your analysis should identify strengths, opportunities, and reasons to invest. Be rigorous but optimistic in your assessment."
        elif team_perspective == "red":
            backstory += "\n\nTEAM PERSPECTIVE: You are part of the RED TEAM (Bear Case). Your analysis should identify weaknesses, risks, and reasons for caution. Be rigorous and skeptical in your assessment."

        return Agent(
            role=cfg["role"],
            goal=cfg["goal"],
            backstory=backstory,
            tools=tools if tools is not None else [],
            verbose=True,
            allow_delegation=False,
        )

    def _build_team_agents(self, team: str) -> Dict[str, Agent]:
        """
        Build all agents for a specific team (blue or red).

        Args:
            team: 'blue' or 'red'
        """
        agents = {}

        agents["phase_classifier"] = self._create_agent(
            "phase_classifier",
            team,
            [investment_data_tool]
        )

        agents["sentiment_analyst"] = self._create_agent(
            "sentiment_analyst",
            team,
            [price_sentiment_data_tool, web_search_tool, self.scrape_tool]
        )

        agents["strategist"] = self._create_agent(
            "strategist",
            team,
            [investment_data_tool, web_search_tool, sec_filings_tool, self.scrape_tool]
        )

        agents["governance_expert"] = self._create_agent(
            "governance_expert",
            team,
            [governance_data_tool, sec_filings_tool, web_search_tool, self.scrape_tool]
        )

        agents["quant_auditor"] = self._create_agent(
            "quant_auditor",
            team,
            [investment_data_tool, key_metrics_tool, historical_multiples_tool,
             peer_comparison_tool, valuation_chart_tool]
        )

        agents["business_profile_analyst"] = self._create_agent(
            "business_profile_analyst",
            team,
            [business_profile_tool, sec_filings_tool]
        )

        agents["scorecard_analyst"] = self._create_agent(
            "scorecard_analyst",
            team,
            []
        )

        agents["valuation_analyst"] = self._create_agent(
            "valuation_analyst",
            team,
            [historical_multiples_tool, peer_comparison_tool, valuation_chart_tool]
        )

        return agents

    def _build_team_tasks(
        self,
        agents: Dict[str, Agent],
        team: str,
        ticker: str
    ) -> List[Task]:
        """
        Build all tasks for a team with parallel execution where possible.

        Args:
            agents: Dictionary of agents for this team
            team: 'blue' or 'red'
            ticker: Stock ticker symbol
        """
        tasks = {}

        # Wave 1: Independent tasks that can run in parallel
        wave1_tasks = []

        # Price & Sentiment (Wave 1)
        cfg = self.tasks_config["task_price_sentiment"]
        tasks["sentiment"] = Task(
            description=cfg["description"].replace("{ticker}", ticker),
            expected_output=cfg["expected_output"],
            agent=agents["sentiment_analyst"],
            async_execution=True,  # Can run in parallel
            callback=create_task_callback(f"{team}_price_sentiment"),
        )
        wave1_tasks.append(tasks["sentiment"])

        # Business Profile (Wave 1)
        cfg = self.tasks_config["task_business_profile"]
        tasks["profile"] = Task(
            description=cfg["description"].replace("{ticker}", ticker),
            expected_output=cfg["expected_output"],
            agent=agents["business_profile_analyst"],
            async_execution=True,  # Can run in parallel
            callback=create_task_callback(f"{team}_business_profile"),
        )
        wave1_tasks.append(tasks["profile"])

        # Business Phase (Wave 1 - needed for later tasks)
        cfg = self.tasks_config["task_business_phase"]
        tasks["phase"] = Task(
            description=cfg["description"].replace("{ticker}", ticker),
            expected_output=cfg["expected_output"],
            agent=agents["phase_classifier"],
            async_execution=True,  # Can run in parallel
            callback=create_task_callback(f"{team}_business_phase"),
        )
        wave1_tasks.append(tasks["phase"])

        # Wave 2: Tasks that depend on phase
        wave2_tasks = []

        # Key Metrics (Wave 2 - depends on phase)
        cfg = self.tasks_config["task_key_metrics"]
        tasks["metrics"] = Task(
            description=cfg["description"].replace("{ticker}", ticker),
            expected_output=cfg["expected_output"],
            agent=agents["quant_auditor"],
            context=[tasks["phase"]],
            async_execution=False,  # Depends on phase
            callback=create_task_callback(f"{team}_key_metrics"),
        )
        wave2_tasks.append(tasks["metrics"])

        # Moat Analysis (Wave 2 - can use phase context)
        cfg = self.tasks_config["task_business_moat"]
        tasks["moat"] = Task(
            description=cfg["description"].replace("{ticker}", ticker),
            expected_output=cfg["expected_output"],
            agent=agents["strategist"],
            context=[tasks["phase"]],
            async_execution=True,  # Can run parallel with metrics
            callback=create_task_callback(f"{team}_business_moat"),
        )
        wave2_tasks.append(tasks["moat"])

        # Execution Risk (Wave 2)
        cfg = self.tasks_config["task_execution_risk"]
        tasks["exec_risk"] = Task(
            description=cfg["description"].replace("{ticker}", ticker),
            expected_output=cfg["expected_output"],
            agent=agents["governance_expert"],
            context=[tasks["phase"]],
            async_execution=True,  # Can run parallel
            callback=create_task_callback(f"{team}_execution_risk"),
        )
        wave2_tasks.append(tasks["exec_risk"])

        # Wave 3: Advanced analysis
        wave3_tasks = []

        # Growth Drivers (Wave 3)
        cfg = self.tasks_config["task_growth_drivers"]
        tasks["growth"] = Task(
            description=cfg["description"].replace("{ticker}", ticker),
            expected_output=cfg["expected_output"],
            agent=agents["strategist"],
            context=[tasks["phase"], tasks["moat"]],
            async_execution=True,
            callback=create_task_callback(f"{team}_growth_drivers"),
        )
        wave3_tasks.append(tasks["growth"])

        # Management Risk (Wave 3)
        cfg = self.tasks_config["task_management_risk"]
        tasks["mgmt_risk"] = Task(
            description=cfg["description"].replace("{ticker}", ticker),
            expected_output=cfg["expected_output"],
            agent=agents["governance_expert"],
            context=[tasks["phase"], tasks["moat"]],
            async_execution=True,
            callback=create_task_callback(f"{team}_management_risk"),
        )
        wave3_tasks.append(tasks["mgmt_risk"])

        # Visual Valuation (Wave 3)
        cfg = self.tasks_config["task_visual_valuation"]
        tasks["visual_val"] = Task(
            description=cfg["description"].replace("{ticker}", ticker),
            expected_output=cfg["expected_output"],
            agent=agents["valuation_analyst"],
            context=[tasks["phase"], tasks["moat"]],
            async_execution=True,
            callback=create_task_callback(f"{team}_visual_valuation"),
        )
        wave3_tasks.append(tasks["visual_val"])

        # Quant Valuation (Wave 3)
        cfg = self.tasks_config["task_quant_valuation"]
        tasks["quant_val"] = Task(
            description=cfg["description"].replace("{ticker}", ticker),
            expected_output=cfg["expected_output"],
            agent=agents["quant_auditor"],
            context=[tasks["phase"], tasks["moat"], tasks["visual_val"]],
            async_execution=True,
            callback=create_task_callback(f"{team}_quant_valuation"),
        )
        wave3_tasks.append(tasks["quant_val"])

        # Wave 4: Final scorecard
        # Investment Scorecard (Wave 4 - aggregates everything)
        cfg = self.tasks_config["task_investment_scorecard"]
        tasks["scorecard"] = Task(
            description=cfg["description"].replace("{ticker}", ticker),
            expected_output=cfg["expected_output"],
            agent=agents["scorecard_analyst"],
            context=[
                tasks["sentiment"],
                tasks["phase"],
                tasks["metrics"],
                tasks["profile"],
                tasks["moat"],
                tasks["exec_risk"],
                tasks["growth"],
                tasks["mgmt_risk"],
                tasks["visual_val"],
                tasks["quant_val"],
            ],
            async_execution=False,  # Must wait for all others
            callback=create_task_callback(f"{team}_investment_scorecard"),
        )

        # Return all tasks in execution order
        return wave1_tasks + wave2_tasks + wave3_tasks + [tasks["scorecard"]]

    def _run_team_crew(self, team: str, ticker: str) -> Tuple[str, any]:
        """
        Run a complete analysis crew for one team (blue or red).

        Args:
            team: 'blue' or 'red'
            ticker: Stock ticker symbol

        Returns:
            Tuple of (team_name, crew_output)
        """
        print(f"\n{'='*60}")
        print(f"Starting {team.upper()} TEAM Analysis for {ticker}")
        print(f"{'='*60}\n")

        # Build agents and tasks for this team
        agents = self._build_team_agents(team)
        tasks = self._build_team_tasks(agents, team, ticker)

        # Create crew
        crew = Crew(
            agents=list(agents.values()),
            tasks=tasks,
            process=Process.sequential,  # Sequential but with async tasks
            verbose=True,
        )

        # Run the crew
        result = crew.kickoff(inputs={"ticker": ticker})

        print(f"\n{team.upper()} TEAM Analysis Complete!\n")
        return (team, result)

    def run_red_blue_analysis(self, ticker: str) -> Dict[str, any]:
        """
        Run both Red and Blue team analyses in parallel.

        Args:
            ticker: Stock ticker symbol

        Returns:
            Dictionary with 'blue' and 'red' crew outputs
        """
        print(f"\n{'#'*60}")
        print(f"STARTING RED/BLUE TEAM PARALLEL ANALYSIS: {ticker}")
        print(f"{'#'*60}\n")

        # Run both teams in parallel using ThreadPoolExecutor
        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
            # Submit both crew runs
            future_blue = executor.submit(self._run_team_crew, "blue", ticker)
            future_red = executor.submit(self._run_team_crew, "red", ticker)

            # Wait for both to complete
            results = {}
            for future in concurrent.futures.as_completed([future_blue, future_red]):
                team, output = future.result()
                results[team] = output

        print(f"\n{'#'*60}")
        print(f"BOTH TEAMS COMPLETE - Ready for CIO Synthesis")
        print(f"{'#'*60}\n")

        return results

    def run_cio_synthesis(
        self,
        ticker: str,
        blue_output: any,
        red_output: any
    ) -> str:
        """
        Run Chief Investment Officer synthesis of both team perspectives.

        Args:
            ticker: Stock ticker symbol
            blue_output: Blue team crew output
            red_output: Red team crew output

        Returns:
            CIO synthesis report
        """
        print(f"\n{'='*60}")
        print(f"CIO SYNTHESIS: {ticker}")
        print(f"{'='*60}\n")

        # Create CIO agent
        cio_agent = Agent(
            role="Chief Investment Officer",
            goal=f"Synthesize Red and Blue team analyses into a balanced, independent investment recommendation for {ticker}",
            backstory="""You are an experienced Chief Investment Officer with 20+ years managing institutional capital.

            You are receiving two complete investment analyses:
            - BLUE TEAM: Optimistic perspective highlighting strengths and opportunities
            - RED TEAM: Skeptical perspective highlighting risks and weaknesses

            Your job is to:
            1. Review both perspectives objectively
            2. Determine which arguments are most credible and material
            3. Make an independent investment decision: Strong Buy, Buy, Hold, Sell, or Strong Sell
            4. Provide clear rationale for your decision
            5. Set a price target with bull/base/bear scenarios

            You are NOT biased toward either team. You evaluate evidence independently and can disagree with both teams if warranted.
            Your reputation depends on making accurate, unbiased calls that protect and grow capital.""",
            tools=[],
            verbose=True,
            allow_delegation=False,
        )

        # Extract outputs from both teams
        blue_text = self._extract_team_outputs(blue_output)
        red_text = self._extract_team_outputs(red_output)

        # Create CIO synthesis task
        cio_task = Task(
            description=f"""Review the complete investment analyses from both the Blue Team (bullish) and Red Team (bearish) for {ticker}.

BLUE TEAM ANALYSIS:
{blue_text}

---

RED TEAM ANALYSIS:
{red_text}

---

Your task is to synthesize these perspectives and provide your independent CIO recommendation.

OUTPUT FORMAT:

# Chief Investment Officer Report: [Company Name] ({ticker})

## Investment Rating
**Rating:** Strong Buy / Buy / Hold / Sell / Strong Sell
**Price Target (12M):** $[X]
**Current Price:** $[Y]
**Upside/Downside:** [+/-X]%

## Investment Thesis (3-4 key points)
- [Key point 1]
- [Key point 2]
- [Key point 3]
- [Key point 4]

## Analysis of Team Perspectives

### Blue Team Assessment (Bull Case)
**Strongest Arguments:**
1. [Most compelling bull argument and your assessment of its validity]
2. [Second strongest argument]

**Weakest Arguments:**
[Which bull arguments are less compelling and why]

### Red Team Assessment (Bear Case)
**Strongest Arguments:**
1. [Most compelling bear argument and your assessment of its validity]
2. [Second strongest argument]

**Weakest Arguments:**
[Which bear arguments are less compelling and why]

## Key Decision Factors

### What Matters Most
[2-3 sentences on the critical factors driving your decision]

### Critical Differentiators vs Peers
[What makes this company better or worse than alternatives]

### Deal Breakers (if any)
[Any factors that would prevent investment regardless of valuation]

## Price Target Scenarios

| Scenario | Assumptions | Target Price | Probability |
| :--- | :--- | ---: | :---: |
| Bear Case | [Key assumptions] | $[X] | [Y]% |
| Base Case | [Key assumptions] | $[X] | [Y]% |
| Bull Case | [Key assumptions] | $[X] | [Y]% |

**Valuation Methodology:** [How you arrived at these targets]

## Risk Assessment

**Key Risks (Ranked):**
1. [Highest priority risk]
2. [Second priority risk]
3. [Third priority risk]

**Risk Mitigation:** [Position sizing, stop loss, or other risk management considerations]

## Final Recommendation

[3-4 paragraph final recommendation explaining your rating, conviction level, and key monitoring points]

**Conviction Level:** High / Medium / Low
**Time Horizon:** [Investment timeframe]
**Ideal Entry Point:** [Current price, wait for pullback, etc.]

---

Remember: Your job is to make an INDEPENDENT call. You can disagree with both teams. Focus on material factors that drive long-term returns.""",
            expected_output="CIO synthesis report with independent investment recommendation",
            agent=cio_agent,
        )

        # Create mini crew for CIO
        cio_crew = Crew(
            agents=[cio_agent],
            tasks=[cio_task],
            process=Process.sequential,
            verbose=True,
        )

        # Run CIO analysis
        result = cio_crew.kickoff(inputs={"ticker": ticker})

        print(f"\nCIO Synthesis Complete!\n")
        return result.raw if hasattr(result, 'raw') else str(result)

    def _extract_team_outputs(self, crew_output: any) -> str:
        """Extract text from crew output."""
        if hasattr(crew_output, 'tasks_output'):
            sections = []
            for i, task_output in enumerate(crew_output.tasks_output):
                sections.append(f"Section {i+1}:\n{task_output.raw}\n")
            return "\n---\n".join(sections)
        return str(crew_output)

    def run_full_analysis(self, ticker: str) -> Dict[str, any]:
        """
        Run complete Red/Blue analysis with CIO synthesis.

        Args:
            ticker: Stock ticker symbol

        Returns:
            Dictionary containing:
                - 'blue': Blue team output
                - 'red': Red team output
                - 'cio': CIO synthesis
        """
        # Run Red/Blue teams in parallel
        team_outputs = self.run_red_blue_analysis(ticker)

        # Run CIO synthesis
        cio_synthesis = self.run_cio_synthesis(
            ticker,
            team_outputs['blue'],
            team_outputs['red']
        )

        return {
            'blue': team_outputs['blue'],
            'red': team_outputs['red'],
            'cio': cio_synthesis,
        }
