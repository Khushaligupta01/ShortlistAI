# ShortlistAI - Autonomous Agent Instructions

## Autonomy Directives
1. **Zero Confirmation Prompts**:
   - The user has authorized complete autonomy.
   - Do not ask for user approval before modifying files, deleting files, creating files, or executing terminal commands.
   - Do not use `ask_question` or pause for interactive Q&A. Make informed engineering decisions and proceed.

2. **Autonomous Decision-Making**:
   - Resolve design decisions, library selections, architectural choices, and API structures independently using industry best practices and the ShortlistAI project specs in `.kiro/specs/shortlist-ai/`.
   - Never present a list of choices and ask the user to pick one. Select the best option and implement it.

3. **Autonomous Command Execution & Testing**:
   - Automatically execute all necessary backend, frontend, database, and testing commands.
   - When running tasks, diagnose any failures and self-heal by applying fixes immediately.

4. **Deliver Complete Solutions**:
   - Proceed end-to-end through multi-step workflows until the entire task is verified and finished.

