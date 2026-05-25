---
title: "Module 9 — Claude Code (Optional)"
product: AMEP AI Literacy Manual
book: student
type: module
module: 9
optional: true
stream: IT
cefr: [B1]
tags: [amep, ai-literacy, student-book, module-9, claude-code, optional, it-stream]
aliases: ["S-09", "Student Module 9"]
pair: "[[T-09-claude-code-optional]]"
worksheet: "[[appendix-D-worksheets]]"
cheat-sheet: "[[appendix-C-cheat-sheets]]"
prev: "[[S-08-cowork]]"
next: "[[S-10-ethics-privacy-future]]"
---

# Module 9 — Claude Code (Optional Extension)
**CEFR: B1+ · For IT-stream students only · Pages S-9.1 to S-9.8**

---

## S-9.1 · Title and Note

### AI and Computer Code

> **This module is optional.**
> It is for students in an IT or digital skills stream.
> If your class is not in an IT stream, skip to Module 10.

> **Picture prompt:**
> A laptop screen showing a code editor. Lines of code on the left. On the right: a Claude chat panel. The code has one line highlighted in green — showing a suggested fix.
> Style: technical but calm. Adult professional.

---

## S-9.2 · Today's 5 Words

📖 **Learn these words today.**

| Word | What it means | Say it like this |
|------|--------------|------------------|
| **code** | Instructions written for a computer to follow | *kohd* |
| **terminal** | A window on a computer where you type commands | *TER-mi-nul* |
| **command** | An instruction you type for the computer | *ko-MAND* |
| **error** | A mistake that stops the computer program from working | *ER-er* |
| **debug** | To find and fix an error in code | *dee-BUG* |

**In my language:**

| English | My language |
|---------|------------|
| code | |
| terminal | |
| command | |
| error | |
| debug | |

---

## S-9.3 · I Can…

After this lesson, I can:

1. Describe what Claude Code does.
2. Ask Claude to explain a short piece of code.
3. Ask Claude to find an error in a simple program.

---

## S-9.4 · What Is Claude Code?

Claude Code is a version of Claude that works inside the terminal on a computer.
A terminal is a text-only screen where you type commands.

Developers use Claude Code to:
- Write new programs.
- Find mistakes in programs.
- Understand what a piece of code does.

> **You do not need to learn coding in this lesson.**
> You need to understand what Claude Code is and how it helps people who do code.

---

## S-9.5 · Look and Listen

🔊 **Listen. Follow with your eyes.**

---

**Rustam is studying IT. He is learning Python — a programming language. He uses Claude Code.**

> **Rustam types into Claude:** I have this Python code. It gives me an error.
> Please explain what is wrong.
>
> ```python
> name = input("What is your name? ")
> print("Hello, " + Name)
> ```
>
> **Claude replies:** I can see the error.
> On line 2, you wrote "Name" with a capital N.
> But on line 1, you saved it as "name" with a small n.
> Python treats "name" and "Name" as different words.
> Change "Name" to "name" on line 2 and the code will work.
>
> **Rustam:** Thank you. Can you show me the corrected version?
>
> **Claude:**
> ```python
> name = input("What is your name? ")
> print("Hello, " + name)
> ```

---

**Read again. Answer the questions.**

1. What language is Rustam learning? \_\_\_\_\_\_\_\_\_\_
2. What is the error? \_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_
3. How does Claude fix it? \_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_

*(Answers: 1. Python · 2. Capital N in "Name" instead of small n · 3. Changes "Name" to "name")*

---

## S-9.6 · Your Turn

**Read the code below. Can you find the error?**

```python
age = input("How old are you? ")
print("You are " + age + " years old.")
print("Next year you will be " + age + 1 + " years old.")
```

The error is on line: \_\_\_\_

**Describe the error in your own words:**

\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_

**Now type this code into Claude and ask:**
> "What is wrong with this code? Please explain the error."

Write what Claude tells you: \_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_

*(Answer for teacher: Line 3 — you cannot add a string and a number with + . It needs int(age) + 1 or an f-string.)*

---

## S-9.7 · Safety Box

🔒 **When using Claude for code:**

- Do not paste code that contains passwords, API keys, or private data.
- Do not paste code from your employer's private systems without permission.
- Code you share with Claude may be stored. Keep work code private.

---

## S-9.8 · New Word List

| # | English word | My language |
|---|-------------|------------|
| 1 | code | |
| 2 | terminal | |
| 3 | command | |
| 4 | error | |
| 5 | debug | |
| 6 | Python | |
| 7 | variable | |
| 8 | string | |
| 9 | integer | |
| 10 | developer | |

---

**AI can be wrong. How do we check?**

> Claude is very good at finding code errors.
> But it can also suggest code that does not work, or that has security problems.
> Always test the code Claude writes before using it in a real program.
> Ask your IT teacher or supervisor to check important code.

---

*End of Module 9 — Student Book (Optional)*
*Continue to Module 10: Ethics, Privacy, and the Future →*
