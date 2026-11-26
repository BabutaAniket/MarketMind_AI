# Simple MarketMind AI demo

## What this app does

MarketMind helps a small business team prepare marketing campaigns using information the business has approved.

It can:

1. Save basic information about a company and its product.
2. Find useful facts from that information.
3. Prepare campaign ideas and draft messages.
4. Help review a possible customer enquiry.
5. Ask a person before saving or “publishing” anything.

For this demo, the company and customer are made up. Nothing is really posted, emailed, or sent to a CRM.

## Start the demo

On the laptop with Docker installed, open PowerShell in the project folder and run:

```powershell
.\scripts\prepare_demo.ps1
```

When it says the app is ready, open <http://localhost:8000> and create an account. Use a demo-only email and a password of at least 12 characters. Accounts and their saved demo data are kept in the Docker volume until you reset it.

The script clears the demo's saved Docker data before it starts. This gives you a clean demo, but removes data saved by an earlier demo.

If Docker is not available, start the app directly:

```powershell
.\.venv\Scripts\python.exe -m marketmind
```

Then open <http://127.0.0.1:8000> and create an account or sign in. Ollama is optional. If it is not running, the main demo still works.

## Before people arrive

- Make sure the app opens.
- Create/sign in to the demo account before the presentation.
- Keep just one browser tab open and set zoom to 100%.
- Use the sample company. Do not enter real customer information.
- If you want to show the optional AI model, make sure Ollama is running and `qwen3:4b` is installed.
- If something goes wrong, skip that part and continue. The main story still works without the model.

## The demo (about 7 minutes)

### 1. Introduce the app — 30 seconds

**Show:** The first screen and the status at the top.

**Say:**

> MarketMind helps a small business plan marketing using its own approved information. It can prepare drafts and help review enquiries. A person stays in control, and this demo does not send anything outside the app.

### 2. Add the sample company — 1 minute

**Show:** Open **Company**. Click **Load sample company**, then **Save knowledge**.

**What this part does:** Saves the basic facts the rest of the app can use.

**Say:**

> This is a made-up company called Cedarline Studio. I’m saving what its product does so the app has facts to work from instead of making them up.

### 3. Find a product fact — 1 minute

**Show:** Open **Search**. Search for: `What are the main customer benefits?`

**What this part does:** Finds relevant sentences in the saved company information and shows where they came from.

**Say:**

> Here the app finds information from the company details we just saved. I can check the source before using it in a campaign.

### 4. Make a campaign plan — 2 minutes

**Show:** Open **Campaign**. Leave the example details as they are. Click **Run approval workflow**.

**What this part does:** Puts together the campaign steps, checks the request, and prepares something for a person to review.

**Say:**

> I’m asking for a campaign to reach small project teams. The app works through the request and stops before taking an action. I can read exactly what it wants to do.

When the review box appears, point out the text and buttons.

**Say:**

> I can approve this, change it, or reject it. If I change it, I need to review the changed version too.

Click **Approve exact payload**.

**Say:**

> This approval only records a demo action. It does not publish a real post or contact anyone.

### 5. Prepare marketing messages — 1 minute

**Show:** Open **Drafts**. Enter a campaign goal and a call to action, then click **Generate drafts**.

**What this part does:** Creates example messages for different channels and checks them for risky or unsupported wording.

**Say:**

> These are starting drafts for a person to review. The app checks for some risky claims, but a person should still check the wording before using it.

### 6. Review a possible customer — 1 minute

**Show:** Open **Leads**. Enter made-up details:

- Name: `Aarav Sharma`
- Company: `Northstar Projects`
- Phone or email: `aarav@example.com`
- Requirement: `Shared task ownership and due dates`
- Timeline: `This quarter`

Click **Score lead**.

**What this part does:** Gives the enquiry a score to help a person decide what to follow up on. It does not decide on its own whether to contact the person.

**Say:**

> This helps organise enquiries. The score is a guide for a person, not an automatic decision.

### 7. Show the final checks — 1 minute

**Show:** Open **Evaluation** and click **Run evaluation**.

**What this part does:** Tries example safe and unsafe requests against the app's basic safety check.

**Say:**

> This is a small test of the safety check, not proof that every risk is solved. We still need more testing before using the app with real customers.

Finish with:

> The main idea is simple: use the company’s own information, prepare useful marketing work, and let a person check it before anything happens.

## If you have extra time

- **Approvals:** Show the list of items waiting for a person to review.
- **Feedback:** Show where a person can save a lesson for future work.
- **Search sources:** Open a search result and point out the source details.
- **Optional AI model:** If Qwen is running, show its status. Be clear about which output came from the model and which came from the app's built-in templates.

## Simple answers to common questions

**Does it send real posts or emails?**

No. Actions in this demo are examples only.

**Does it always use an AI model?**

No. The main demo can run without one. A local model can be used for some optional text generation.

**Can it make mistakes?**

Yes. The drafts and scores are suggestions. People need to check them.

**Is it ready for real customer data?**

No. This is a prototype. It needs more security, privacy, and real-world testing first.
