# How AI Agents Use VibeSafe

## Claude Code

```bash
# Install the skill:
claude plugin install https://github.com/nerudek/vibe-safe

# Or manually copy skill file:
cp skills/vibe-safe.md ~/.claude/skills/vibe-safe.md
```

Then in any session:
```
/vibe-safe
```

Claude will automatically invoke the skill before any code that installs packages.

---

## Kimi (Moonshot)

Kimi doesn't have a plugin system, but reads skill files as context.

Add to Kimi's startup prompt:
```
Read and follow this skill for any coding task:
$(cat /Volumes/2TB_APFS/projekty/vibe-safe/skills/vibe-safe.md)
```

Or via ACP:
```bash
npx acpx kimi exec "Read /Volumes/2TB_APFS/projekty/vibe-safe/skills/vibe-safe.md and apply it before writing code"
```

---

## Hermes / Vox (DeepSeek)

Add to HARNESS.md Section §14 (the content is in `harness/SECURITY-POLICY.md`):

```bash
cat /Volumes/2TB_APFS/projekty/vibe-safe/harness/SECURITY-POLICY.md >> \
  /Volumes/2TB_APFS/openclaw-data/workspace/obsidian-memory/agents/ALL/HARNESS.md
```

Hermes loads HARNESS on every session start, so this becomes automatic.

For manual invocation in Hermes session:
```bash
npx acpx hermes exec "Run vibe-safe pre-flight: bash /Volumes/2TB_APFS/projekty/vibe-safe/tools/audit.sh $(pwd)"
```

---

## OpenClaw

OpenClaw is a gateway — it runs tools via webhooks, not LLM skills.

Add to OpenClaw config as a pre-tool hook:
```json
{
  "hooks": {
    "before_code_generation": "/Volumes/2TB_APFS/projekty/vibe-safe/tools/audit.sh {{project_path}}"
  }
}
```

Or trigger manually:
```bash
npx acpx openclaw exec "audit /current/project"
```

---

## VS Code (Copilot / Continue / Cursor)

1. Copy the tasks file to your project:
```bash
cp vscode/.vscode/tasks.json /your/project/.vscode/tasks.json
```

2. Update the tool path in tasks.json to point to your vibe-safe installation.

3. Run audit: `Cmd+Shift+P → Tasks: Run Task → VibeSafe: Audit Project`

4. For auto-run on project open: the `runOn: folderOpen` flag in tasks.json handles this.

For Cursor AI: Add the skill content to `.cursorrules`:
```bash
echo "SECURITY RULE: Before installing any package, run vibe-safe pre-flight:" >> .cursorrules
cat skills/vibe-safe.md >> .cursorrules
```

For Continue.dev: Add to `.continue/config.json` as a system prompt addition.

---

## GitHub Copilot (VS Code extension)

Add to `.github/copilot-instructions.md`:
```markdown
## Security Pre-Flight (VibeSafe)

Before suggesting code that installs external packages:
1. List all planned libraries with alternatives considered
2. Note any known CVEs or maintenance concerns
3. Confirm secrets stay in .env, not source code
4. Suggest running: `./tools/audit.sh` before coding starts
```

---

## Generic LLM / API usage

Pass the skill as a system prompt:
```python
import anthropic

with open("skills/vibe-safe.md") as f:
    vibe_safe_skill = f.read()

client = anthropic.Anthropic()
response = client.messages.create(
    model="claude-sonnet-4-6",
    system=f"You are a coding assistant. Follow this security protocol:\n\n{vibe_safe_skill}",
    messages=[{"role": "user", "content": "Build me a Node.js API"}]
)
```

---

## CrewAI integration

```python
from crewai import Agent, Task, Crew
from crewai_tools import tool
import subprocess

@tool("vibesafe_audit")
def vibesafe_audit(project_path: str) -> str:
    """Run VibeSafe security pre-flight on a project directory."""
    result = subprocess.run(
        ["bash", "/path/to/vibe-safe/tools/audit.sh", project_path, "--json"],
        capture_output=True, text=True
    )
    return result.stdout or result.stderr

security_agent = Agent(
    role="Security Pre-Flight Officer",
    goal="Audit dependencies before any code is written",
    backstory="You ensure no vulnerable or unmaintained packages enter the codebase.",
    tools=[vibesafe_audit],
    verbose=True
)

audit_task = Task(
    description="Run VibeSafe pre-flight on {project_path} and report findings",
    agent=security_agent,
    expected_output="stay_safe.md certificate status and list of any issues"
)
```

---

## LangChain integration

```python
from langchain.tools import tool
from langchain_anthropic import ChatAnthropic
from langchain.agents import create_tool_calling_agent, AgentExecutor
import subprocess, json

@tool
def vibesafe_audit(project_path: str) -> dict:
    """Audit a project's dependencies for CVEs and maintenance issues."""
    result = subprocess.run(
        ["python3", "/path/to/vibe-safe/tools/audit.py", project_path, "--json"],
        capture_output=True, text=True, timeout=120
    )
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError:
        return {"error": result.stderr, "status": "ERROR"}

llm = ChatAnthropic(model="claude-sonnet-4-6")
tools = [vibesafe_audit]
agent = create_tool_calling_agent(llm, tools, prompt)
executor = AgentExecutor(agent=agent, tools=tools, verbose=True)
```
