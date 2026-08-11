#!/usr/bin/env python3
"""Read a long document once, then ask several questions about it.

The point of this script is the timing it prints. The first call pays prefill for the
whole document; every question after it reuses the context already resident in the KV
cache, which on this board is the difference between tens of minutes and about a minute.

Start the server first, with a context large enough for the document and --parallel 1 so
one slot gets the whole window:

    llama-server -m ~/models/muse-glimmer-30B-kquant-17gb.gguf \\
        -t 8 -c 32768 --parallel 1 --jinja --host 127.0.0.1 --port 8080

Then:  ./manual_qa.py iq9075-manual.txt
"""
import json
import sys
import time
import urllib.request

URL = "http://127.0.0.1:8080/v1/chat/completions"

QUESTIONS = [
    "How much RAM does this board have, and what type and speed is it?",
    "How many Ethernet ports does the EVK have, and at what speed?",
    "Which Wi-Fi and Bluetooth versions does it support?",
    "What storage options are available on this board?",
]


def ask(messages, max_tokens=220):
    body = json.dumps({"messages": messages, "max_tokens": max_tokens}).encode()
    req = urllib.request.Request(URL, data=body,
                                 headers={"Content-Type": "application/json"})
    t0 = time.time()
    with urllib.request.urlopen(req, timeout=7200) as r:
        d = json.loads(r.read())
    dt = time.time() - t0
    msg = d["choices"][0]["message"]
    return msg.get("content") or "", d.get("usage", {}), dt


def main():
    path = sys.argv[1] if len(sys.argv) > 1 else "iq9075-manual.txt"
    document = open(path).read()

    # "Reasoning strength" is read from the system message, not from a command-line flag.
    system = ("You answer questions about the Qualcomm Dragonwing IQ-9075 using only the "
              "documentation provided. Be brief and quote figures exactly.\n\n"
              "Reasoning strength: low.")

    # The document rides in the first user turn so it becomes a cacheable prefix.
    messages = [
        {"role": "system", "content": system},
        {"role": "user", "content": "Here is the documentation:\n\n" + document
                                    + "\n\nAcknowledge with one word."},
    ]
    print(f"document: {len(document)} characters", flush=True)

    print("=== reading the document (this call pays prefill) ===", flush=True)
    answer, usage, dt = ask(messages, max_tokens=12)
    print(f"[read] {dt:.1f}s  prompt_tokens={usage.get('prompt_tokens')}", flush=True)
    messages.append({"role": "assistant", "content": answer})

    print("=== questions (document already resident) ===", flush=True)
    for i, question in enumerate(QUESTIONS, 1):
        messages.append({"role": "user", "content": question})
        answer, usage, dt = ask(messages)
        cached = usage.get("prompt_tokens_details", {}).get("cached_tokens")
        print(f"\n--- Q{i}  {dt:.1f}s  prompt_tokens={usage.get('prompt_tokens')} "
              f"cached={cached} completion={usage.get('completion_tokens')} ---", flush=True)
        print(f"Q: {question}", flush=True)
        print(f"A: {answer.strip()}", flush=True)
        messages.append({"role": "assistant", "content": answer})


if __name__ == "__main__":
    main()
