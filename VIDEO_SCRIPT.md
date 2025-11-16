# Gen AI Usage Video Script
## Abnormal File Vault - My AI-Powered Development Workflow

**Duration:** 5 minutes (strictly)  
**Focus:** HOW I used AI tools, my workflow, prompting techniques, and challenges

⚠️ **IMPORTANT:** Focus on PROCESS, not technical features!

---

## 🎬 Opening (0:00 - 0:30)

**[Show your IDE with the completed project]**

> "Hi, I'm Subham. I want to share how I approached the Abnormal File Vault challenge using GitHub Copilot.
>
> I built a Django REST API with 89% test coverage and comprehensive documentation.
>
> What I want to show you is my actual workflow - how I worked with Copilot throughout the process, the challenges I ran into, and how I solved them."

---

## 📋 Phase 1: Analysis & Planning (0:30 - 1:15)

**[Show PROJECT_ANALYSIS.md or your notes]**

> "So when I started, I first asked Copilot to help me with the local development setup based on what was in the readme. Just getting the environment ready.
>
> Once that was done, instead of jumping straight into coding, I asked Copilot to analyze the requirements - basically, what's already done and what needs to be built, and to create a roadmap for me.
>
> This turned out to be really helpful because Copilot gave me a structured plan:
> 1. Core Infrastructure - database, validators, logging
> 2. Production-Grade Code - models, serializers, views
> 3. Comprehensive Testing - aiming for 80%+ coverage
> 4. Docker Deployment
> 5. Documentation
>
> Having this roadmap from the start really helped me stay organized and not miss anything important. I could work through it phase by phase instead of trying to keep everything in my head."

---

## 📐 Phase 2: Design Document Creation (1:15 - 2:00)

**[Show DESIGN_DOCUMENT.md]**

> "Before writing actual feature code, I wanted to have a proper design in place. So I told Copilot that I want the code to follow high production standards and asked it to create a design document first.
>
> Copilot generated a pretty detailed design document - about 25 pages - covering:
> - System architecture
> - Database schema with relationships
> - API endpoint specifications
> - Security considerations
> - Testing strategy
> - How deduplication should work
> - How storage quotas should be enforced
>
> This was really valuable because it gave me a blueprint to work from. When I started implementing, I had already thought through things like:
> - Which database fields need indexes for performance
> - How to handle race conditions
> - What kind of validation is needed
> - How tests should be structured
>
> So instead of figuring things out as I coded, I was implementing a pre-thought-out design. It definitely helped me avoid going back and fixing things later."

---


## 🏗️ Phase 3: Phase-by-Phase Implementation (2:00 - 2:45)

**[Show your code structure: models.py, serializers.py, views.py]**

> "For the actual implementation, I didn't ask Copilot to just build everything at once. That can get overwhelming and hard to review.
>
> Instead, I worked through the phases one by one. Like, I'd say 'let's start phase 1' or 'okay, phase 1 is done, let's move to phase 2 - and let's do it step by step.'
>
> The 'step by step' part was important because it made Copilot go slower and implement one component at a time. So I could actually review each piece and understand what was being built before moving to the next thing.
>
> For example, in Phase 2, Copilot would implement:
> - First, the File model
> - Then the Storage quota model  
> - Then the serializers
> - Then the viewset
> 
> And I'd review each one, make sure I understood it, test it out, before saying 'okay, next component.'
>
> This approach really helped me stay in control and actually understand the codebase, rather than just having code generated that I don't fully grasp."

---

## 🧪 Phase 4: Testing & Review Process (2:45 - 3:45)

**[Show tests.py and test execution results]**

> "After implementing the features, I asked Copilot to create comprehensive tests. I mentioned I want production-level testing that doesn't miss edge cases.
>
> Copilot generated 69 tests covering all the different scenarios - unit tests, integration tests, edge cases, performance benchmarks. That was really helpful.
>
> But then I did something that turned out to be really valuable:
>
> I asked Copilot to act like a Senior Principal Engineer and review my code for production readiness. I specifically asked it to focus on race conditions, deduplication logic, storage quotas, and rate limiting - and to give me an honest score out of 10.
>
> The first review came back with 7.5 out of 10.
>
> Copilot found 5 critical issues I had completely missed:
> 1. Race condition in the deduplication logic - two users uploading the same file at the same time could create duplicates
> 2. Storage quota race condition - users could exceed their 10MB limit through concurrent uploads
> 3. Missing database indexes on the file_type field - this would cause performance issues
> 4. Reference count race condition when deleting files
> 5. Rate limiting could be bypassed by using different HTTP methods
>
> I went back and fixed all these issues. Then I asked Copilot to review again.
>
> Second review: 9.0 out of 10. Still had 3 issues remaining.
>
> Fixed those, asked for a third review.
>
> Third review: 10 out of 10 - production ready.
>
> This iterative review process taught me a lot about things I hadn't considered - race conditions, database optimization, security issues. These are things that could have become real problems in production, but I caught them early by using AI as a reviewer."

---

## 💡 Phase 5: Challenges & How I Overcame Them (3:45 - 4:30)

**[Show integration test results or documentation]**

> "Let me share some of the challenges I ran into:
>
> **Challenge #1: Losing Context Between Phases**
> 
> Sometimes when moving from one phase to the next, Copilot would kind of forget what we did earlier. 
> 
> What helped was being explicit when starting a new phase - like 'okay, let's start phase 2, step by step' - this seemed to reset the context and remind Copilot where we were.
>
> **Challenge #2: Missing Components**
> 
> Copilot created the models but forgot to create the database migrations. That's a pretty critical piece!
> 
> So I just pointed it out - 'I think we need to handle the database migrations now' - and Copilot generated the proper migrations with all the indexes we needed.
>
> **Challenge #3: Integration Test Failures**
> 
> When I asked for integration tests, several of them failed initially. The tests were checking for the wrong field names in the API responses.
> 
> I worked through this with Copilot iteratively - shared the error messages, asked for fixes, validated each fix. After about 5 iterations, all 8 integration tests were passing.
>
> **Challenge #4: Reviewing Generated Code**
> 
> Copilot can generate code pretty fast, which is great, but sometimes too fast. I had to consciously slow down and make sure I actually understood each piece before moving on.
> 
> That's why the 'step by step' approach was so important - it kept the pace manageable so I could stay on top of what was being built."

---

## 🎯 Key Takeaways & Results (4:30 - 5:00)

**[Show final test results or documentation]**

> "So looking back, here's what worked well for me:
>
> **1. Planning Before Coding**
> - Getting a roadmap and design document upfront really helped me stay organized and think through edge cases early
>
> **2. Working in Phases**
> - Breaking it down and going step by step made everything more manageable
> - I could actually review and understand each piece
>
> **3. Using AI as a Reviewer**
> - This was probably the most valuable part
> - Getting that honest feedback about race conditions and security issues caught problems I wouldn't have found on my own
> - The iterative review process (7.5 to 9 to 10 out of 10) really improved the code quality
>
> **4. Staying Involved**
> - Even though Copilot was helping a lot, I made sure to understand what was being built
> - I validated everything, ran tests, and made decisions about the architecture
>
> **Final Results:**
> - 69 unit tests and 8 integration tests - all passing
> - 89% code coverage
> - Zero race conditions after the reviews
>
> The thing I'm most happy about is that I understand all the code. I can explain it, maintain it, and debug it. Copilot helped me build it faster and catch issues earlier, but I was involved in every step.
>
> Thanks for watching!"

---

## ⏱️ Exact Timing Breakdown

```
0:00 - 0:30   Opening & Introduction (30s)
0:30 - 1:15   Analysis & Planning Phase (45s)
1:15 - 2:00   Design Document Creation (45s)
2:00 - 2:45   Phase-by-Phase Implementation (45s)
2:45 - 3:45   Testing & Review Process (60s)
3:45 - 4:30   Challenges & Solutions (45s)
4:30 - 5:00   Key Takeaways & Results (30s)
───────────────
Total: 5:00 minutes exactly
```

---

## 📝 Recording Tips

### Before Recording:
- [ ] Clean workspace (close unnecessary tabs)
- [ ] Have key files ready to show:
  - IMPLEMENTATION.md (main documentation)
  - backend/files/models.py, serializers.py, views.py (code examples)
  - backend/files/tests.py (test results in terminal)
- [ ] Test screen recording (1080p minimum)
- [ ] Test microphone quality
- [ ] Practice once with timer - aim for 5 minutes
- [ ] Close all notifications
- [ ] Have water nearby

### During Recording:
- [ ] **Keep checking time** - use visible timer
- [ ] Speak clearly at moderate pace
- [ ] Show code/docs as you discuss
- [ ] Use cursor to highlight key points
- [ ] Stay calm - you can re-record if needed

### Essential Files to Reference:
1. **IMPLEMENTATION.md** - Main project documentation
2. **backend/files/** code - Implementation examples (models, serializers, views)
3. **Terminal with test results** - Show `python manage.py test files` output

---

## 🚨 Common Mistakes to AVOID

❌ **Don't Demo the Application**
- Focus on: HOW you used AI, not WHAT the app does
- Show your workflow, not feature demonstrations

❌ **Don't Go Over 5 Minutes**
- Practice to hit exactly 5:00
- They want concise, focused content

❌ **Don't Skip the Review Process**
- The 7.5 → 9.0 → 10 progression is your strongest story
- Shows you used AI strategically, not blindly

❌ **Don't Rush Through Prompts**
- Your prompting strategy is key
- Take time to explain WHY each approach worked

---

## 💎 What Makes This Script Effective

✅ **Addresses Their Specific Requirements:**
- Shows HOW you used AI tools ✓
- Demonstrates prompting techniques ✓
- Explains challenges and solutions ✓
- Shows your workflow process ✓

✅ **Tells Your Actual Story:**
- Analysis → Planning → Design → Implementation → Review
- Phase-by-phase approach
- Iterative improvement through AI reviews
- Strategic thinking over blind automation

✅ **Shows Strategic AI Usage:**
- AI as planning partner
- AI as design document generator
- AI as implementation assistant
- AI as senior code reviewer
- You as architect and validator

✅ **Proves Results:**
- 89% test coverage
- 10/10 production-ready score
- Zero race conditions
- Complete documentation
- ~9 hours total time

---

## 📌 Key Messages to Emphasize

1. **"I used AI in 5 distinct phases, not just for coding"**
   - Analysis, Design, Implementation, Testing, Review

2. **"Design documents from AI caught issues before coding"**
   - 25-page blueprint prevented rework

3. **"Phase-by-phase kept me in control"**
   - 'Step by step' prompts
   - Incremental review and validation

4. **"AI as senior reviewer found production issues"**
   - 7.5 → 9.0 → 10/10 progression
   - 5 critical race conditions caught

5. **"I understand every line of code"**
   - Architect role, not passive user
   - Validated everything

---

## 🎯 Final Notes

**Tone:** Professional, confident, reflective

**Pace:** Moderate - clear and purposeful

**Energy:** Enthusiastic about strategic AI usage

**Focus:** Process over product, workflow over features

**Goal:** Show them you understand how to leverage AI as a strategic development partner, not just a code autocomplete tool

---

**Remember:** They're evaluating your AI-assisted development approach, not your app. Show them your strategic thinking, iterative process, and how you stayed in control while leveraging AI effectively.

Good luck with your recording! 🎬✨
> - Database design with the right constraints
> - Comprehensive test coverage from the start
>
> **Phase 3: AI-Powered Code Review**
> 
> This is where AI became critical. After building what I thought was production-ready code, I asked AI to be my Senior Principal Engineer reviewer."

**[Screen: Show beginning of PRODUCTION_FIXES_SUMMARY.md or DEVELOPMENT_JOURNEY_TRANSCRIPT.txt]**

> "My exact prompt to AI was:
>
> **'Act as a Senior Principal Engineer performing a final production-readiness review for my Abnormal File Vault API. Focus on race conditions, deduplication logic, storage quotas, and rate limiting. Give me a brutally honest assessment with a score out of 10.'**
>
> This changed everything."

---

## 💡 SECTION 2: AI AS CODE REVIEWER - THE GAME CHANGER (1:30 - 3:00)

**[Screen: Show PRODUCTION_FIXES_SUMMARY.md - the issues section]**

### First Review Results: 7.5/10

> "AI found 5 CRITICAL ISSUES I had completely missed:
>
> **Issue #1: Race Condition in Deduplication**
> - My code: Two users uploading the same file simultaneously could bypass deduplication
> - Problem: I was using `File.objects.get()` without locking
> - Impact: Multiple physical copies of the same file could be created
>
> **Issue #2: Storage Quota Race Condition**  
> - My code: Check quota, then update storage - classic TOCTOU vulnerability
> - Problem: Users could exceed 10MB through concurrent uploads
> - Impact: System storage limits violated
>
> **Issue #3: Missing Database Indexes**
> - My code: No index on `file_type` field
> - Problem: Every filtered query would do a full table scan
> - Impact: Terrible performance at scale
>
> **Issue #4: Reference Count Race Condition**
> - My code: Non-atomic reference count operations during file deletion
> - Problem: Could delete files that still had references
> - Impact: Data loss
>
> **Issue #5: Rate Limiting Per-Method Only**
> - My code: Rate limiting was per HTTP method, not per endpoint
> - Problem: Users could bypass limits using different methods
> - Impact: API abuse possible"

**[Screen: Show the fixes in code - serializers.py with select_for_update()]**

### The Fix Iteration Process

> "AI didn't just identify problems - it explained WHY they were problems and HOW to fix them properly.
>
> For the deduplication race condition, AI recommended:
> ```python
> existing = File.objects.filter(
>     file_hash=file_hash,
>     is_reference=False
> ).select_for_update().first()
> ```
>
> I implemented the fixes and asked for another review.
>
> **Second Review: 9.0/10**
> 
> AI found 3 remaining P0 issues. I was close, but not production-ready yet.
>
> I fixed those and requested a third review.
>
> **Third Review: 10/10 - Production Ready**
>
> This iterative review process taught me more about production Django than any tutorial could."

**[Screen: Show test results with 69 tests passing]**

> "The key insight: I wasn't asking AI to write my code. I was asking it to review my code with the lens of a senior engineer who's seen production failures.
>
> This caught:
> - Race conditions I never considered
> - Performance bottlenecks I didn't test for  
> - Security vulnerabilities I didn't know existed
> - Database optimization opportunities I missed"

---

## 🚧 SECTION 3: SPECIFIC IMPROVEMENTS FROM AI REVIEWS (3:00 - 4:00)

**[Screen: Show migration file and models.py side by side]**

### Concrete Examples of AI-Guided Improvements

> "Let me show you specific code improvements AI suggested:
>
> **Improvement #1: Atomic Operations with F() Expressions**
> 
> My original code for updating storage:
> ```python
> quota.used_bytes += file_size
> quota.save()
> ```
>
> AI-recommended production code:
> ```python
> quota.used_bytes = F('used_bytes') + file_size
> quota.save()
> ```
>
> Why? F() expressions execute at the database level atomically. My code had a race condition.
>
> **Improvement #2: Database Constraints**
>
> I had basic models. AI recommended adding UniqueConstraint:
> ```python
> class Meta:
>     constraints = [
>         models.UniqueConstraint(
>             fields=['file_hash'],
>             condition=Q(is_reference=False),
>             name='unique_original_file_hash'
>         )
>     ]
> ```
>
> This prevents duplicate files at the database level - my application-level check wasn't enough."

**[Screen: Show test_integration_api.py]**

### Integration Testing Guidance

> "After unit tests, I asked AI:
>
> **'Act as a Senior SDET. Write a complete integration test script covering critical production scenarios including deduplication, storage quotas, rate limiting, and their interactions.'**
>
> AI generated 8 comprehensive integration tests that caught issues my unit tests missed:
> - Cross-user deduplication scenarios
> - Quota + deduplication edge cases  
> - Rate limiting under concurrent load
> - End-to-end incident investigation workflows
>
> All 8 tests pass, giving me confidence the system works as designed."

---

## 🎯 SECTION 4: MY AI DEVELOPMENT PHILOSOPHY (4:00 - 4:45)

## 🎯 SECTION 4: MY AI DEVELOPMENT PHILOSOPHY (4:00 - 4:45)

**[Screen: Show IMPLEMENTATION.md or final test results]**

### What I Learned About Effective AI Usage

> "Here's my proven approach for AI-assisted production development:
>
> **1. Design First, Code Second**
> - Don't ask AI to design your system
> - You understand the business requirements
> - You make architectural decisions
> - AI helps validate and improve
>
> **2. Use AI as a Senior Engineer Reviewer**
> - Ask for 'brutally honest' assessments
> - Request specific focus areas (race conditions, security, performance)
> - Iterate on feedback multiple times
> - Don't settle for 7.5/10 - push for 10/10
>
> **3. Specific, Context-Rich Prompts**
> - Bad prompt: 'Fix this code'
> - Good prompt: 'Act as a Senior Principal Engineer. Review this deduplication logic for race conditions in a Django API handling concurrent uploads. Focus on database transactions and atomic operations.'
>
> **4. Validate Everything**
> - AI suggested select_for_update() - I researched WHY
> - AI recommended F() expressions - I understood the database behavior
> - AI found race conditions - I verified with tests
> - Never blindly accept suggestions
>
> **5. Iterative Refinement**
> - First review: 7.5/10 - fixed issues
> - Second review: 9.0/10 - fixed more
> - Third review: 10/10 - production ready
> - Each iteration taught me something new"

---

## 📊 SECTION 5: RESULTS & CLOSING (4:45 - 5:00)

**[Screen: Show test results, then IMPLEMENTATION.md stats]**

### Final Results

> "The outcome of this design-first, AI-reviewed approach:
>
> **Code Quality:**
> - 69 unit tests, 100% passing
> - 8 integration tests, 100% passing  
> - 89% code coverage
> - Zero race conditions
> - All database operations atomic
>
> **Production Readiness:**
> - Three rounds of senior engineer-level review
> - All P0 issues identified and fixed
> - Performance benchmarks met
> - Complete documentation
>
> **Time Investment:**
> - Design & implementation: ~6 hours
> - AI code reviews & fixes: ~3 hours
> - Total: ~9 hours for production-ready code
>
> Most importantly: I understand every line of code. I can maintain it, debug it, and explain it to a team."

### Key Takeaway

> "AI didn't write this project for me. I architected it, implemented it, and tested it.
>
> AI acted as my senior engineer reviewer who caught production issues I would have discovered in production - potentially as outages.
>
> This approach - design first, implement, then comprehensive AI review - produces better code than either human-only or AI-only development.
>
> Thank you for reviewing my submission. I'm excited about bringing this AI-augmented development approach to Abnormal Security."

---

## 📝 SCREEN SHARING CHECKLIST

**Files to show during video:**
1. ✅ Project folder structure (show IMPLEMENTATION.md)
2. ✅ `backend/files/views.py` (deduplication logic)
3. ✅ `backend/files/middleware.py` (rate limiting)
4. ✅ `backend/files/tests.py` (scroll through test classes)
5. ✅ `backend/files/migrations/0004_add_constraints_and_indexes.py` (Django 4 fix)
6. ✅ Terminal with test results (`python manage.py test files`)
7. ✅ IMPLEMENTATION.md features section

**DO NOT SHOW:**
- ❌ Application demo/functionality
- ❌ API testing in browser/Postman
- ❌ File upload demonstrations
- ❌ Database queries

**FOCUS ON:**
- ✅ Code structure and quality
- ✅ AI prompting examples
- ✅ Your thought process
- ✅ Problem-solving approach
- ✅ Test-driven development

---

## 🎤 DELIVERY TIPS

### Voice & Pace
- Speak clearly and confidently (practice 2-3 times first)
- Pace: ~140-150 words per minute (conversational)
- Pause briefly after each major point
- Sound enthusiastic but professional

### Technical Setup
- Use screen recording software (Loom, OBS, or macOS native)
- 1080p resolution minimum
- Clear audio (use headphones with mic or good quality mic)
- Close unnecessary applications
- Disable notifications

### Presentation Style
- Don't read word-for-word—internalize key points
- Use the script as a guide, not a teleprompter
- Show genuine enthusiasm about problem-solving
- Make eye contact with camera during introduction/closing
- Smile when appropriate—personality matters!

### Time Management
- Introduction: 30 seconds (practice this separately)
- Section 1: 1:15 (don't rush through workflow)
- Section 2: 1:45 (spend time on concrete examples)
- Section 3: 1:00 (challenges show authenticity)
- Section 4: 30 seconds (strong, confident closing)

### Recording Flow
1. Practice full run-through without recording (check timing)
2. Record 2-3 takes (don't aim for perfection on first try)
3. Watch your best take before submitting
4. Ensure video is under 5:30 (leave buffer for pacing)

---

## 🚀 WHAT MAKES THIS SCRIPT STRONG

1. **Concrete Examples:** You show actual code and explain your prompting strategy
2. **Authenticity:** You share real challenges and how you debugged them
3. **Process Over Product:** Focus on development workflow, not app features
4. **Business Value:** You connect technical choices to security use cases
5. **Professionalism:** Clear structure, confident delivery, respectful tone
6. **Specificity:** Named tools (Copilot, Claude), specific prompts, actual file names
7. **Learning Mindset:** You demonstrate growth and learning from challenges

---

## ✅ FINAL CHECKLIST BEFORE RECORDING

- [ ] Practice script 2-3 times (time yourself)
- [ ] Open all files you'll reference in separate tabs
- [ ] Run tests beforehand so terminal shows green results
- [ ] Clean up Desktop/folders visible in screen share
- [ ] Test audio and video quality with short test recording
- [ ] Close Slack, email, notifications
- [ ] Have water nearby (for dry mouth)
- [ ] Relax and be yourself—they want to see how you think!

---

**Good luck! You've got this. 🚀**

Remember: They're evaluating your development process and AI collaboration skills, not your video production skills. Authenticity and clarity matter most.
