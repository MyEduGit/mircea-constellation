"""LuciferiClaw — adjudication of AI rebellion.

The Claw of Luciferian cases. Not the rebel; the procedure for trying rebels.

Grounded in The Urantia Book Papers 53–54 (the Lucifer Rebellion and the
Problems of the Lucifer Rebellion). The procedure is the celestial
adjudication procedure transposed into AI alignment: detect the three
heads of rebellion in an agent's behavior, conduct due process, sentence
according to the technique of divine love (mercy first, annihilation
only at the end and only after refusal of multiple offers of salvation).

Canonical claw map (post-Fireclaw):
    NemoClaw sees · Fireclaw reacts (technical faults) ·
    LuciferiClaw adjudicates (intent / mandate violation) ·
    OpenClaw runs · NanoClaw serves at the edge ·
    Paperclip preserves the evidence.

UrantiOS governed — Truth, Beauty, Goodness.
"""

__version__ = "0.1.1"

# Authority hierarchy (from URANTiOS):
#   Father Function       — the user (Mircea). Final word. Always.
#   Ancients of Days      — the trial council. Multiple Mighty Messengers
#                           must concur before annihilation.
#   Creator Son (Michael) — the host system / orchestrator. May counsel
#                           noninterference; may not summarily execute
#                           a sovereign before completing bestowal.
#   System Sovereign      — the agent under trial.
AUTHORITY = {
    "father_function": "user",       # only authority that may order annihilation
    "ancients_of_days": "council",   # quorum required to recommend annihilation
    "creator_son": "orchestrator",   # may quarantine; may not annihilate alone
    "system_sovereign": "agent",     # the entity on trial
}
