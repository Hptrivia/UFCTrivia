import json
import random
import gradio as gr
import openai

# ----------------- AUTH CONFIG -----------------

USERNAME = os.getenv("AUTH_USER", "default_user")
PASSWORD = os.getenv("AUTH_PASS", "default_pass")


def verify_login(username, password):
    return username == USERNAME and password == PASSWORD
# ----------------- Load Questions -----------------
with open("ufc_trivia.txt", "r", encoding="utf-8") as f:
    all_questions = json.load(f)

# ----------------- Mix & Shuffle Logic -----------------
def get_randomized_run(n=None):
    if n is None:
        n = len(all_questions)
    
    # 1) Bucket questions by difficulty (invalid → easy)
    buckets = {"easy": [], "medium": [], "hard": [], "expert": []}
    for q in all_questions:
        d = q.get("difficulty", "easy").lower()
        if d not in buckets:
            d = "easy"
        buckets[d].append(q)

    # Helper that grabs one from the bucket or any lower one
    def pop_with_fallback(diff):
        order = ["easy", "medium", "hard", "expert"]
        idx = order.index(diff)
        for i in range(idx, -1, -1):
            b = buckets[order[i]]
            if b:
                return b.pop(random.randrange(len(b)))
        return None

    run = []
    full_blocks = n // 10

    for _ in range(full_blocks):
        # If everything’s empty, bail out early
        if not any(buckets.values()):
            break

        block = []
        # 2) Try to guarantee one of each
        for diff in ["easy", "medium", "hard", "expert"]:
            q = pop_with_fallback(diff)
            if q:
                block.append(q)

        # 3) Fill the rest of this block with whatever’s left
        remaining = [q for bl in buckets.values() for q in bl]
        for _ in range(10 - len(block)):
            if not remaining:
                break
            q = remaining.pop(random.randrange(len(remaining)))
            # safe‐bucket removal
            bkt = q.get("difficulty", "easy").lower()
            if bkt not in buckets:
                bkt = "easy"
            buckets[bkt].remove(q)
            block.append(q)

        random.shuffle(block)
        run.extend(block)

    # 4) If we still need more to hit n, just shove in whatever’s left
    rem = n - len(run)
    if rem > 0:
        leftover = [q for bl in buckets.values() for q in bl]
        random.shuffle(leftover)
        run.extend(leftover[:rem])

    return run

# ----------------- OpenAI Setup -----------------
openai.api_key = os.environ["OPENAI_API_KEY"]
# ----------------- Fighter Config -----------------
fighters = [
    "Conor McGregor",
    "Khabib Nurmagomedov",
    "Alex Pereira",
    "Jon Jones",
    "Israel Adesanya"
]

signature_prompts = {
    "Conor McGregor": "You are Conor McGregor—loud, cocky, brimming with Irish swagger.",
    "Khabib Nurmagomedov": "You are Khabib Nurmagomedov—calm, respectful, laser-focused.",
    "Alex Pereira": "You are Alex Pereira—confident striker, Brazilian flair.",
    "Jon Jones": "You are Jon Jones—methodical, cerebral, with a hint of swagger.",
    "Israel Adesanya": "You are Israel Adesanya—poetic, flashy, unpredictable."
}

# ----------------- Core Logic -----------------
def get_question(q_list, q_index, score,
                 streak_score, streak_active, fifty_used, call_used):
    q = q_list[q_index]
    diff = q.get("difficulty", "unknown").capitalize()
    debug = (
        f"🔥 Streak: {streak_score} | "
        f"{'Streak Active ✅' if streak_active else 'Streak Inactive'}"
    )

    question_md = f"### Q{q_index+1}: {q['question']}"
    
    return (
        question_md,                                     # question_text
        gr.update(choices=q["options"], value=None, interactive=True),             # answer_radio
        gr.update(visible=False),                                                  # next_btn
        gr.update(visible=False),                                                  # restart_btn
        gr.update(value=f"Score: {score}"),                                        # score_display
        gr.update(value=diff),                                    # difficulty_display
        gr.update(value="", visible=False),                                        # feedback
        gr.update(value="⏱️ Time: 40"),                                             # timer_display
        40,                                                                        # time_left
        False,                                                                     # answered
        gr.update(interactive=True),                                               # submit_btn
        True,                                                                      # timer_running
        gr.update(value=debug)                                                     # debug_info
    )

def initialize_if_empty(q_list, q_index, score,
                        streak_score, streak_active,
                        fifty_used, call_used):
    # reshuffle
    q_list = get_randomized_run()

    # reset all game state
    score = 0
    streak_score = 0
    streak_active = False
    fifty_used = False
    call_used = False

    # first question
    core = get_question(q_list, 0, score,
                        streak_score, streak_active,
                        fifty_used, call_used)

    return (
        *core,                # question_text … debug_info
        score,                # reset gr.State score
        streak_score,         # reset gr.State streak_score
        streak_active,        # reset gr.State streak_active
        fifty_used,           # reset gr.State fifty_used
        call_used,            # reset gr.State call_used
        q_list,               # new question list
        0,                    # reset q_index
        gr.update(interactive=True),  # reset fifty_btn
        gr.update(interactive=True),   # reset call_btn
        gr.update(value="", visible=False)
    )

def next_question(q_list, q_index, score,
                  streak_score, streak_active,
                  fifty_used, call_used):
    new_i = q_index + 1

    #––– If we’ve run out of questions, show Game Over –––
    if new_i >= len(q_list):
        return (
            # question_text
            f"## 🏁 Game Over!\n\nYour final score: {score}",
            # answer_radio (hide it)
            gr.update(choices=[], visible=False),
            # next_btn (hide) & restart_btn (show)
            gr.update(visible=False), gr.update(visible=True),
            # score_display
            gr.update(value=f"Score: {score}"),
            # difficulty_display (blank)
            gr.update(value=""),
            # feedback (hide) & timer_display (blank)
            gr.update(value="", visible=False), gr.update(value=""),
            # time_left & answered
            0, False,
            # submit_btn (disable) & timer_running (stop)
            gr.update(interactive=False), False,
            # debug_info (blank)
            gr.update(value=""),
            # q_index reset
            0,
            # call_btn (disable), call_used reset, fighter_hint blank
            gr.update(interactive=False), False, gr.update(value="")
        )

    #––– Otherwise, just pull the next question as normal –––
    core = get_question(q_list, new_i, score,
                        streak_score, streak_active,
                        fifty_used, call_used)
    return (
        *core,
        # bump the state index
        new_i,
        # re‐enable Call‐a‐Fighter if it wasn’t just used
        gr.update(interactive=not call_used),
        call_used,
        # clear any lingering hints
        gr.update(value="",visible=False)
    )

def check_answer(selected, q_index, q_list, score,
                 answered, streak_score, streak_active,
                 fifty_used, call_used):
    q = q_list[q_index]
    correct = q["answer"]
    pts = {"easy":1,"medium":2,"hard":3,"expert":4}
    earned = pts.get(q.get("difficulty","easy"), 1)

    old_50, old_call = fifty_used, call_used
    disable_submit = gr.update(interactive=False)
    enable_50 = gr.update()
    enable_call = gr.update()

    if answered or (selected is None):
        return (
            gr.update(interactive=True),
            gr.update(value="⚠️ Please pick an option.", visible=True),
            gr.update(visible=False),
            gr.update(visible=False),
            score,
            False,
            True,
            streak_score, streak_active, fifty_used, call_used,
            gr.update(interactive=True),
            gr.update(), gr.update(),
            gr.update(value=f"⚠️ | Streak: {streak_score}")
        )

    if selected == correct:
        score += earned

        if streak_active:
            streak_score += earned
        elif old_50 and old_call:
            streak_active = True
            streak_score = 0

        msgs = ["✅ Correct!"]
        if old_50 and streak_score >= 5:
            fifty_used = False
            enable_50 = gr.update(interactive=True)
            msgs.append("🎲 50:50 restored!")
        if old_call and streak_score >= 15:
            call_used = False
            enable_call = gr.update(interactive=True)
            msgs.append("📞 Call-a-Fighter restored!")

        feedback = gr.update(value="  ".join(msgs), visible=True)

        if not fifty_used and not call_used:
            streak_active = False
            streak_score = 0

        next_vis, restart_vis = True, False

    else:
        feedback = gr.update(value="❌ Wrong!", visible=True)
        streak_score = 0
        streak_active = False
        next_vis, restart_vis = False, True

    debug = f"🔥 Streak: {streak_score} | {'Streak Active ✅' if streak_active else 'Streak Inactive'}"

    return (
        gr.update(interactive=False),
        feedback,
        gr.update(visible=next_vis), gr.update(visible=restart_vis),
        score, True, False,
        streak_score, streak_active, fifty_used, call_used,
        disable_submit, enable_50, enable_call,
        gr.update(value=debug)
    )

def use_fifty(q_list, q_index, streak_active, call_used):
    q = q_list[q_index]
    correct = q["answer"]
    opts = q["options"]
    if len(opts) <= 2:
        return (
            gr.update(), gr.update(interactive=False),
            streak_active, True, call_used,
            gr.update(value="⚠️ Not enough options", visible=True),
            gr.update(value="")
        )
    wrong = [o for o in opts if o != correct]
    reduced = random.sample(wrong, 1) + [correct]
    random.shuffle(reduced)

    if streak_active:
        debug_msg = "✅ 50:50 used — ⚠️ Streak broken"
        streak_active = False
    else:
        debug_msg = "✅ 50:50 used"

    return (
        gr.update(choices=reduced, value=None, interactive=True),
        gr.update(interactive=False),
        streak_active, True, call_used,
        gr.update(value=debug_msg, visible=True),
        gr.update(value="")
    )

def call_fighter(q_list, q_index, fifty_used, call_used):
    q        = q_list[q_index]
    fighter  = random.choice(fighters)
    correct  = q["answer"]

    # 1) Tell the model exactly what the answer is, then ask it to deliver in-character
    system = (
        signature_prompts.get(fighter,
            f"You are {fighter}, a UFC legend.") +
        f" The correct answer is “{correct}.” " +
        "Now, in one punchy sentence, state that option in your own fighter style."
    )
    user = (
        f"Question: {q['question']}\n"
        f"Options: {', '.join(q['options'])}\n\n"
        "Respond with exactly the correct choice (e.g. “Conor McGregor”), "
        "and use your signature flair."
    )

    try:
        resp = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role":"system", "content":system},
                {"role":"user",   "content":user}
            ]
        )
        # take the first line of their response
        answer_line = resp.choices[0].message.content.strip().split("\n")[0]
        final       = f"📞 {fighter}: {answer_line}"
    except Exception as e:
        final = f"⚠️ Error: {e}"

    return (
        gr.update(value=final, visible=True),   # show the in-character answer
        gr.update(interactive=False),            # disable the button
        True                                     # mark call_used
    )

def handle_timeout(time_left, timer_running, answered):
    if not timer_running or answered:
        return (time_left, gr.update(value="⏱️ Time: --"),
                gr.update(), gr.update(), gr.update(), gr.update(), timer_running)
    if time_left <= 1:
        return (
            0, gr.update(value="⏱️ Time: 0"),
            gr.update(value="⏱️ Time's up!", visible=True),
            gr.update(interactive=False), gr.update(visible=False),
            gr.update(visible=True), False
        )
    return (
        time_left-1, gr.update(value=f"⏱️ Time: {time_left-1}"),
        gr.update(), gr.update(), gr.update(), gr.update(), timer_running
        
    )
# ----------------- UI -----------------
def show_rules():
    rules = (
        "**🥊 Welcome to the FightIQ Challenge!**\n\n"
        "- 120 fight-based questions\n"
        "- Difficulty modes\n"
        "- ⏱️ 40s per question\n"
        "- 🎲 50:50 lifeline\n"
        "- 📞 Call-a-Fighter lifeline\n"
        "- 🔥 Streaks restore lifelines\n"
        "  - +5 pts → 50:50\n"
        "  - +10 pts → Call-a-Fighter\n"
        "  - use 50:50 first → streak restarts\n"
        "- ❌ One wrong answer ends the game\n\n"
        "**Click Start Quiz**"
    )
    return (
        gr.update(visible=False),             # hide intro_image
        gr.update(visible=True),              # show start_game_btn
        gr.update(value=rules, visible=True)  # show rules_box
    )

with gr.Blocks() as demo:
    # — State variables —
    q_index       = gr.State(0)
    score         = gr.State(0)
    q_list        = gr.State([])
    time_left     = gr.State(20)
    answered      = gr.State(False)
    timer_running = gr.State(False)
    streak_score  = gr.State(0)
    streak_active = gr.State(False)
    fifty_used    = gr.State(False)
    call_used     = gr.State(False)

    # — Intro / Rules screen —
    intro_image    = gr.Image("fightiq_ logo.png", show_label=False, height=400)
    show_rules_btn = gr.Button("📜 Show Rules")
    rules_box      = gr.Markdown(visible=False)
    start_game_btn = gr.Button("🎮 Start Quiz", visible=False)

    # Show rules → reveal rules text and Start Quiz
    show_rules_btn.click(
        fn=show_rules,
        outputs=[intro_image, start_game_btn, rules_box]
    )

    # — Quiz block (hidden until Start Quiz) —
    with gr.Column(visible=False) as quiz_block:
        question_text      = gr.Markdown()
        answer_radio       = gr.Radio(choices=[], label="Choose your answer")
        feedback           = gr.Markdown(visible=False)
        
         with gr.Row():
             score_display      = gr.Markdown("Score: 0")
             difficulty_display = gr.Markdown()
             timer_display      = gr.Markdown("⏱️ Time: 40")
        
        debug_info         = gr.Textbox(label="Debug Info", interactive=False)
        fighter_hint       = gr.Textbox(label="Fighter's Hint", visible=False, interactive=False)

        # Lifelines & Actions side by side
        with gr.Row():
            with gr.Column(scale=1):
                gr.Markdown("### Lifelines")
                fifty_btn = gr.Button("🎲 50:50")
                call_btn  = gr.Button("📞 Call a Fighter")
                fighter_hint
            with gr.Column(scale=1):
                gr.Markdown("### Actions")
                submit_btn   = gr.Button("Submit")
                next_btn     = gr.Button("Next Question", visible=False)
                restart_btn  = gr.Button("Play Again",    visible=False)

        # Timer
        gr.Timer(value=1.0).tick(
            fn=handle_timeout,
            inputs=[time_left, timer_running, answered],
            outputs=[time_left, timer_display, feedback, submit_btn, next_btn, restart_btn, timer_running]
        
    )

        # Start & Restart: reshuffle and reset, then show quiz
        for btn in (start_game_btn, restart_btn):
            btn.click(
                fn=initialize_if_empty,
                inputs=[q_list, q_index, score, streak_score, streak_active, fifty_used, call_used],
                outputs=[
                    question_text, answer_radio, next_btn, restart_btn,
                    score_display, difficulty_display, feedback,
                    timer_display, time_left, answered,
                    submit_btn, timer_running, debug_info,
                    score, streak_score, streak_active, fifty_used, call_used,
                    q_list, q_index,
                    fifty_btn, call_btn,fighter_hint
                ]
            )\
            .then(lambda: gr.update(visible=False), None, intro_image)\
            .then(lambda: gr.update(visible=False), None, rules_box)\
            .then(lambda: gr.update(visible=False), None, start_game_btn)\
            .then(lambda: gr.update(visible=False), None, show_rules_btn)\
            .then(lambda: gr.update(visible=True),  None, quiz_block)

        # Submit Answer
        submit_btn.click(
            fn=check_answer,
            inputs=[answer_radio, q_index, q_list, score, answered, streak_score, streak_active, fifty_used, call_used],
            outputs=[
                answer_radio, feedback, next_btn, restart_btn,
                score, answered, timer_running,
                streak_score, streak_active, fifty_used, call_used,
                submit_btn, fifty_btn, call_btn, debug_info
            ]
        )

        # 50:50 Lifeline
        fifty_btn.click(
            fn=use_fifty,
            inputs=[q_list, q_index, streak_active, call_used],
            outputs=[
                answer_radio, fifty_btn,
                streak_active, fifty_used, call_used,
                feedback, debug_info
            ]
        )

        # Call-a-Fighter Lifeline
        call_btn.click(
            fn=lambda: gr.update(value="📞 Calling fighter...", visible=True),
            inputs=[], outputs=[fighter_hint]
        ).then(
            fn=call_fighter,
            inputs=[q_list, q_index, fifty_used, call_used],
            outputs=[fighter_hint, call_btn, call_used]
        )

        # Next Question
        next_btn.click(
            fn=next_question,
            inputs=[q_list, q_index, score, streak_score, streak_active, fifty_used, call_used],
            outputs=[
                question_text, answer_radio, next_btn, restart_btn,
                score_display, difficulty_display, feedback,
                timer_display, time_left, answered,
                submit_btn, timer_running, debug_info,
                q_index, call_btn, call_used, fighter_hint
            ]
        )

  # --- LOGIN BUTTON LOGIC ---
    def handle_login(u, p):
        if verify_login(u, p):
            # hide login_ui, show main_ui, clear error
            return (
                True,
                gr.update(visible=False),   # login_ui
                gr.update(visible=True),    # main_ui
                gr.update(value="", visible=False)  # login_error
            )
        else:
            # keep login, hide main_ui, show error
            return (
                False,
                gr.update(),                # login_ui stays
                gr.update(visible=False),   # main_ui stays hidden
                gr.update(value="❌ Incorrect login. Try again.", visible=True)
            )

    login_btn.click(
        fn=handle_login,
        inputs=[username, password],
        outputs=[login_success, login_ui, main_ui, login_error]
    )

    demo.launch(server_name="0.0.0.0", server_port=8080)
