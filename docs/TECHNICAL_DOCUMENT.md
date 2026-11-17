# Northern in Barcelona — technical document

More Than A Hack 2027 · possession per frame (H / A / D) for BAR–ATH from the provided automatic data.

Final submission: `src/v1_14.py`. Everything below is reproducible from this repository plus the
official data bundle. No figure in this document is frame-level data of the provided match; all
numbers about it are aggregate counts.

## 1. Approach

A rule-based pipeline over the provided tracking, with the hard part — the frames where the ball
is missing — decided by two small classifiers that read only the **players**. The classifiers are
trained exclusively on open data from **other games** (IDSSE, Bundesliga) and only applied to BAR–ATH.

Why this shape: the ball is the most informative signal and the least reliable one. We first
measured *how* it goes missing (section 4), and the answer pointed away from "occlusion" and
towards "the tracker drops the ball when play stops, and degrades over each half". Ball-missing
time is where most of the error lives, and during it the only evidence left is collective player
behaviour: how fast they move, whether someone stands on a line, how each team spreads, who
controls the space around the last known ball position.

Pipeline (`src/v1_14.py`):

1. **Nearest player** to the ball, per frame (official baseline).
2. **Short gaps** (≤ 3.0 s) with the same team on both sides are filled with that team.
3. **Majority vote** over ±75 frames (±3 s), then **hysteresis**: possessions shorter than 1.5 s are absorbed.
4. **Every gap of ≥ 3.0 s** becomes a dead-ball candidate. Candidates that overlap a `SET PIECES`
   instance of the provided Smart Tagging (±2 s) stay **D**.
5. **Remaining gaps of ≥ 5 s** (58 in this match) are decided by the players:
   - **P1 — stopped or live?** Logistic model on: relative player intensity, sprinting fraction,
     intensity drop at the moment the ball disappears, team compactness, distance from the nearest
     player to the last ball position, a slow player within 2 m of a line (throw-in / corner /
     goal kick), and players inside the boxes. Probability > 0.5 → **D**.
   - **P2 — if live, which team?** Logistic model on: team advance towards the opponent goal,
     difference in team spread (the team in possession opens up), nearest player to the last ball
     position at the end of the gap, a "receiver" (a player who reaches the last ball position and
     decelerates), a "carry-out" (that player moves away while opponents turn towards him),
     time spent within 5 m of the ball point, numerical superiority within 10 m, local Voronoi
     control of a 15 m disc around the ball point, team running synchrony, counter-attack speed,
     change in team dispersion, plus the last team seen with the ball.
6. Shorter gaps without a set piece keep the possession of the last team (continuation).
7. Frames 110,808–113,741 are **D**, as stated in the official FAQ (graded but before the second-half kickoff).

Result on the full match (aggregates): 295 graded possessions, mean duration 14.0 s, D on 35.1% of
graded frames. Of the 58 gaps decided by the players, 18 became D (416 s), 15 H (153 s), 25 A (289 s).

## 2. Assets used

| asset | used | how |
|---|---|---|
| Tactical ATD (tracking with ball) | **yes** | ball and player positions, team per track slot from the ATD metadata |
| Smart Tagging | **yes** | `SET PIECES` intervals only, to keep restarts as D |
| Homography | no | the ATD is already in pitch coordinates |
| Broadcast video / broadcast ATD | no | not synchronised to the tactical timeline; not needed for this approach |
| Tactical video | no | no own detection or tracking in the final pipeline |
| Public 5-minute ground truth | **only as a pipeline check** | see section 6 |

An AI coding assistant (Claude) was used to help write and review code. No match data was shared
with it: it only saw aggregate statistics computed locally and the open IDSSE data.

Tried and dropped:
- **A rule "long gap without set piece ≥ 18 s → D"** and a **"calm players → D" rule** (earlier
  versions v1.11–v1.12). Their thresholds had been chosen on the public window, which the rules
  forbid, so they were removed and replaced by P1/P2, chosen on IDSSE only.
- **A Bi-LSTM** over player sequences (`src/posse_lstm.py`, after Kim et al., KDD 2023), trained on
  IDSSE. Kept as an informative experiment only (section 5).
- **A "stationary visible ball" detector.** Our measurement showed the ball is visible and
  stationary for ≥ 2 s on only 64 s of the whole match, so the expected gain was too small.

## 3. Training data

| dataset | source | who labelled it | amount | used for |
|---|---|---|---|---|
| IDSSE open tracking + ball state + ball-owning team | Bassek et al., *An integrated dataset of spatiotemporal and event data in elite soccer*, Scientific Data (2025); loaded with `kloppy` (`sportec.load_open_tracking_data`) | the official Bundesliga data provider (DFL / Sportec Solutions), not us | 7 matches: 5 for development (J03WPY, J03WN1, J03WMX, J03WOY, J03WQQ), 2 held out (J03WR9, J03WOH) | choosing the smoothing window and hysteresis; training and testing P1/P2; the LSTM experiment |

Nothing from the provided game was labelled, corrected or used as training data. No human-produced
data about BAR–ATH was used.

**How the IDSSE matches mimic our problem.** IDSSE has the ball almost always visible. To train
and test gap decisions we hide the ball in windows whose lengths follow the gap-length distribution
measured on our match (5–8 s, 8–12 s, 12–20 s, 20–60 s, weighted 38/31/19/44) and compute the
signals from the players and the last known ball position only. Speeds are normalised by each
game's own median, because the two tracking systems measure speed on different scales.

**Held-out results (decision rules written in each script before running):**
- P1 (stopped vs live), combined model: AUC 0.949 mean over development, **0.926 and 0.957** on the
  two held-out matches (rule: ≥ 0.75 on both).
- P2 (which team), combined model vs "last team seen": **+8.5 pp** on development, **+8.8 pp and
  +10.1 pp** on the held-out matches (rule: ≥ +3 pp on both). On "challenges" (≥ 2 players within
  5 m of the last ball position) accuracy goes from 0.68–0.73 to 0.79–0.85 on held-out games.
- Window ±75 / hysteresis 1.5 s: the best development combination (±50 / 1.5 s) did not beat the
  current one on both held-out matches, so the rule kept ±75 / 1.5 s.
- Fill and dead-ball candidate thresholds: the match has **no gap between 1 and 5 s**, so any value
  in 0.5–4.9 s produces the same labels (verified: 0 frames change). We set both to 3.0 s, the middle
  of that empty band.

## 4. What we learned about the missing ball (aggregates of the provided tracking)

- 150 gaps cover 43.1% of all frames; gaps of 20 s or more are 29% of the gaps but 67% of the missing time.
- No gap lasts between 1 and 5 s. Pure occlusion would produce many short gaps.
- 56% of gaps start near a touchline or goal line; 52% coincide with a Smart Tagging set piece.
- 135 of 149 gaps start with a slow ball (< 8 m/s), so motion blur is not the main cause.
- Ball visibility changes a lot over the match. In 10-minute blocks it falls steadily through the
  first half (85% → 74% → 60% → 47% → 41%, and 20% in the short final block), recovers to 78% at the
  second-half kickoff, and then varies without a clean trend (59%, 67%, 34%, 54%, 72%). So a long gap
  does not mean the same thing at every point of the match: sometimes it is a stoppage, sometimes
  lost tracking during live play. That is why a fixed duration threshold was wrong and a
  player-based decision is needed.
- 1.8% of visible-ball frames move faster than 40 m/s, in multi-frame bursts — most likely a high
  ball projected onto the ground plane. Not yet handled (section 7).

## 5. The LSTM experiment (informative)

`analises/lstm_posse_idsse.py` trains a 2-layer Bi-LSTM (5 Hz, 60 s sequences) on the 5 IDSSE
development matches with simulated gaps and compares it with the rules on the held-out matches.
Before seeing any result we declared that the player-signal classifiers (P1/P2) would be the
submission and the LSTM informative only, because choosing between the two would need a fifth use
of the same two held-out matches.

Results (all on IDSSE with the ball hidden, `spellF1`):
- Against the rule pipeline on the held-out matches, the hybrid (rules where the ball is visible,
  LSTM where it is missing) gained +0.045 to +0.113 in all four comparisons, and so passed its own
  pre-declared rule. The pure LSTM falls from 0.79–0.93 on its training matches to 0.44–0.62 on the
  held-out ones, so it overfits the matches it saw.
- In a later leave-one-match-out comparison on the five development matches, the hybrid beat the
  player-signal approach of `v1_14` in 10 of 10 measurements, by +0.067 on average.

That comparison was designed after the LSTM result was known, so under our own protocol it does not
change the choice of submission. The alternative pipeline is kept in `src/v1_15.py` (same base,
LSTM on ball-missing frames, set pieces still D) for transparency.

## 6. Possession rules — where we drew the lines

- **Loose balls and challenges:** while the ball is visible, the nearest player decides, smoothed
  over ±3 s; possessions shorter than 1.5 s are absorbed into the surrounding one. During a gap,
  P2 decides using the receiver, time near the ball, superiority and Voronoi control around the
  last ball position.
- **Restarts:** any gap that overlaps an automatic `SET PIECES` tag is D. Other gaps of ≥ 5 s are
  D when the players behave like a stoppage (P1).
- **Half-time block:** D, as the FAQ states.
- **Abstention (X):** never on graded frames.

**Use of the public ground truth.** It was used only to check that the pipeline is correct
(alignment, file format). No parameter or version choice in the final pipeline depends on it. An
earlier set of thresholds that had been tuned on it was identified and replaced (section 2).
Every experiment, its pre-declared decision rule and its verdict are recorded in
`validacao/REGISTRO.md`, together with sha256 hashes of each script taken before it was run.

## 7. Limitations

- **Simulated gaps.** P1/P2 learn from IDSSE windows where we hid the ball; real tracker losses
  are not random (they cluster at stoppages and late in each half). The held-out gains are an
  upper bound for this match.
- **The "last team" input** comes from the true owner in IDSSE but from nearest-player labels here.
- **Track slots are trajectory fragments**, not players, in the provided ATD; signals that follow
  one player (receiver, carry-out, synchrony) are noisier here than in IDSSE.
- **Gaps longer than 60 s** are beyond the training range (5–60 s).
- **Speed reference.** Player intensity is normalised by the median over live-ball frames in IDSSE,
  but over visible-ball frames here (we do not know which frames are live).
- **What was approved.** P1/P2 were approved on window-level AUC and accuracy, not on end-to-end
  `spellF1`; the training windows were drawn anywhere in the game, not where a tracker loses the ball.
- **P1 threshold** is the plain 0.5; it is not calibrated to this match's share of dead ball.
- The signal code lives in `analises/sinais_jogadores_idsse.py` and is imported by `src/v1_14.py`
  unchanged, so the code that was validated is the code that runs.
- **High balls** (bursts above 40 m/s) still let the nearest player flicker between teams.
- **Held-out matches reused.** IDSSE has 7 matches; the same 2 held-out games served as the final
  test of four experiments.
- With more time: a ball-in-the-air rule validated on data with ball height, an own ball detector
  on the tactical video for in-play gaps, and calibrating the P1 threshold to the match's dead-ball share.

## 8. Reproduction

```bash
git clone --recurse-submodules https://github.com/GregNewze/northern-in-barcelona.git
cd northern-in-barcelona
# data: follow oficial/DATA.md and unpack into oficial/data/tactical/
python3.12 -m venv oficial/.venv
oficial/.venv/bin/pip install -r requirements.txt
oficial/.venv/bin/python src/v1_14.py --saida northern-in-barcelona.csv
oficial/.venv/bin/python oficial/evaluation/validate_submission.py oficial/evaluation/results/northern-in-barcelona.csv
oficial/.venv/bin/python src/testes.py
```

The submission only needs the committed weights in `src/modelo_sinais.json`. To rebuild them from
scratch (downloads the open IDSSE matches through kloppy):

```bash
oficial/.venv/bin/python analises/cache_idsse.py
oficial/.venv/bin/python analises/sinais_jogadores_idsse.py      # the approved experiment
oficial/.venv/bin/python analises/exporta_sinais_idsse.py        # writes src/modelo_sinais.json
```

The output is deterministic: `src/testes.py` checks the sha256 of the labels and of the weights
against `src/snapshot_v1_14.json`.
