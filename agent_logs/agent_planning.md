# Cursor app design and requirements
_Exported on 2/13/2026 at 17:47:30 PST from Cursor (2.4.21)_

---

**User**

I have 2 hours to make anything I want in any language only will code for 1 hour of that though. This will have a python backend and be deployed on vercel. My idea for this is to create a cursor app that sees what your last prompt was to the agent and gives you a suggestion for what the next prompt should be based on what you are building or on how to revert your changes and rewrite the prompt to build it better and ask more spec driven development questions that go into specifics rather than just starting to build right away/ We can use the diff also in the files to check. So basically there should be two modes one where they user uses just the diff without a prompt in the command line and this is the "suggest" mode and another where they use the diff and they also enter their last prompt in the command line which would be the "refine" mode where we will return the rewritten prompt with better design principles and spec driven development in mind. This should just return what was wrong with the prompt along with the new rewritten prompt with spec driven development and detailed requirements in mind. There should be no governance or compliance. rather it should be relatedto architecture and make sure the edge cases are covered. I want to organize it into folders so there should be an app folder which contains the main cli entry point as well as a git diff getter file, a prompt builer section and an llm client. Then in the app folder there should also be an llm folder than has that llm client and prompt builder files. We will use open ai api for requests and the api key etc can be loaded from the .env file. Based on this repo structure and outlines design a prd for the coding agent to use. In addition, this must be deployed on vercel. So another secondary thing we can add is a UI interface where instead of running commands to get the git diff, we have the repo path as an input to the UI, and the user can select to suggest or refine based on the git diff. If they choose to suggest it will only use the diff. Otherwise if they choose to refine they should also input the last prompt that was used. There should be a requirements.txt and tasks in the plan should be delegated so that multiple agents can work in parallel (4)

---

**Cursor**

I’ll quickly scan the repo to confirm what already exists, then I’ll draft a focused PRD with a parallelized 4-agent task breakdown for the coding phase.

I found the repo is empty, so I can shape this from scratch. Before I lock the PRD, I need one scope decision so the 1-hour coding window is realistic.

---

**User**

And lets use openai api for the requests, I'll have my api key but it needs to be deployed so that anyone can use it

---

**Cursor**

To support “anyone can use it” with OpenAI on Vercel, I need one security/product decision before finalizing the PRD and agent task split.

Great, that locks the MVP decisions. I’m creating the PRD plan now with a 4-agent parallel implementation breakdown, aligned to CLI-first + FastAPI + public OpenAI-backed access on Vercel.

---

**User**

The output does not need to be structured json, just needs to be pure text with the rewritten prompt. In the refine case a reason for why the prompt isn't specified enough for reqs spec atec can be given as well

---

**Cursor**

I’ll update the PRD to make outputs plain text (not JSON) and set refine mode to return a short “why underspecified” explanation plus the rewritten spec-driven prompt.

Updated the PRD to match your requirement:

- Output is now **plain text only** (no structured JSON).
- `refine` explicitly includes a **reason section** describing why the prior prompt was underspecified (requirements/spec/acceptance criteria gaps), plus the rewritten prompt.
- API contracts are now defined as **`text/plain` responses**.
- Agent tasks and acceptance criteria were updated accordingly (including stable text section ordering).

If you want, next I can tighten the exact section template for each mode so outputs are highly consistent, e.g.:

- Suggest: `Context` → `Recommended Next Prompt` → `Alternates` → `Edge Cases`
- Refine: `Why Underspecified` → `Rewritten Prompt` → `Assumptions to Confirm` → `Edge Cases`

