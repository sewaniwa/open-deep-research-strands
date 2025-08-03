# Open Deep Research Strands

A recreation of Open Deep Research using Strands Agents multi-agent architecture.

## Overview

This project implements a multi-agent research system using Strands Agents to replicate the capabilities of Open Deep Research. The system features a three-phase control loop with parallel research execution and quality feedback mechanisms.

## Architecture

### Core Components

- **Supervisor Agent**: Orchestrates the entire research process and manages other agents
- **Research Sub-Agents**: Perform specialized research on specific subtopics
- **Scoping Agent**: Handles requirement clarification through interactive dialogue
- **Report Agent**: Integrates research findings into comprehensive reports

### Three-Phase Control Loop

1. **Scoping Phase**: Interactive requirement clarification and research brief generation
2. **Research Phase**: Parallel research execution with quality feedback loops
3. **Report Phase**: Result integration and final report generation

## Project Structure

```
open_deep_research_strands/
├── src/
│   ├── agents/           # Agent implementations
│   ├── workflows/        # Workflow orchestration
│   ├── communication/    # Agent-to-agent communication
│   ├── tools/            # Research tools and utilities
│   ├── evaluation/       # Quality evaluation systems
│   └── config/           # Configuration management
├── tests/                # Test suites
├── local_memory/         # Local memory storage
├── configs/              # Configuration files
└── scripts/              # Utility scripts
```

## Development Phases

### Phase 1: Local Development Environment (Current)
- ✅ Project initialization
- 🔄 Strands Agents SDK setup
- ⏳ Mock services implementation
- ⏳ Basic agent classes
- ⏳ A2A communication system

### Phase 2: Core Feature Implementation
- Multi-agent system implementation
- Three-phase workflow development
- Swarm control systems
- Quality assurance mechanisms

### Phase 3: Bedrock AgentCore Integration
- Cloud runtime migration
- Memory system integration
- Gateway and observability setup
- Identity management

### Phase 4: Evaluation and Optimization
- Quantitative evaluation framework
- Baseline comparison with Open Deep Research
- Performance optimization
- Continuous quality monitoring

## Getting Started

### Prerequisites

- Python 3.9+
- Strands Agents SDK
- OpenAI or Anthropic API access

### Installation

1. Clone the repository
2. Copy `.env.example` to `.env` and configure your API keys
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

### Configuration

Edit `configs/local_config.py` to customize:
- LLM provider settings
- Agent resource limits
- Tool configurations
- Memory settings

## Usage

```python
from src.agents.supervisor_agent import SupervisorAgent

# Initialize the supervisor
supervisor = SupervisorAgent()

# Execute research
result = await supervisor.execute_control_loop("Your research query here")
```

## Testing

Run the test suite:
```bash
pytest tests/
```

## Contributing

1. Follow the four-phase workflow defined in CLAUDE.md
2. Maintain small, focused commits
3. Ensure all tests pass before committing
4. Update documentation as needed

## License

MIT License - see LICENSE file for details