# Claude Code brief — Brainlife reproduction of the Wakeman & Henson MEEG study (ds000117)

## Objective
On Brainlife, reproduce the MEG/EEG group analysis from the target methods paper and the mne-biomag-group-demo pipeline, using the Wakeman & Henson multimodal dataset (ds000117, 16 subjects). Our main goal is to reproduce the figures of the paper analysing this data in MNE (Methods paper below).
Priorities, in order: faithful reproduction → robustness of the Apps → publishing them under BrainlifeMEEG. Harden Apps as you fix them along the way.

## Read first — before proposing any plan
Local:
- root directory: /network/iss/cenir/analyse/meeg/BRAINLIFE/code
- repo description and conventions `agent-instruction.md` + `README.md` at root.
- Apps source code at root.
- Source-reconstruction Apps by user «obVdo» found at https://github.com/obVdo/app-noise-covariance-v2 https://github.com/obVdo/app-freesurfer-v2 https://github.com/obVdo/app-source-space-v2 https://github.com/obVdo/app-coreg-v2 https://github.com/obVdo/app-bem-v2 https://github.com/obVdo/app-forward-v2 https://github.com/obVdo/app-inverse-v2 to be cloned at root.
- Pipeline-generation tooling at «local_scripts/ReproduceProject/» and local_scripts/create_pipeline_rule.py.
- mne Docker file at docker-mne
- mne-freesurfer Dockerfile at docker-mne-freesurfer.
External (fetch if reachable; some Brainlife pages need login — if so, I'll paste the relevant logs):
- Target pipeline: https://mne.tools/mne-biomag-group-demo/auto_scripts/index.html
- Methods paper (Frontiers 2018): https://www.frontiersin.org/journals/neuroscience/articles/10.3389/fnins.2018.00530/full
- Brainlife target project: https://brainlife.io/project/5df7efdc32bff02262e226b6

## Data (already in the project archive)
###meg session: 
- Raw MEEG: tagged "task-facerecognition" "run-##" with runs 01-06"
- MaxFilter derivatives: tagged "proc-sss" "run-##" with runs 01-06
###mri session:
- T1 anat: tagged "acq-mprage"

## Phases
0. **Plan.** Write a short strategy doc: check how the mne-biomag steps map onto Brainlife Apps as described below, the App dependency graph, which Apps need changes, and open questions. **Pause before running anything.**

For the following, develop on one subject first. Use subject 10 run 02 at first. Starting at Figure 4 catch up with subject 3 (all runs). After Figure 5

1. **Reading data.** use fif2mne/raw app: https://brainlife.io/app/628b5c89d0697cf1eaeaffad
2. **Preprocessing (Maxfilter).** Use raw data files and pass them to the Maxwell filtering app: https://brainlife.io/app/602bc6a33a001123014c442a. **Recreate Figure 1 A and B of the paper.** **Pause.**
3. **Compute PSD.** Compute PSD and Recreate Figure 2: PSD of subject 10, run 02 **Pause.**
4. **Temporal Filtering.** Show Filter response as in Figure 3 for mne 1.12 (current version) **Pause.**
5. **Marking bad segments and channels. ICA. Epoching.** Can you think of diagnostic new figures to show? **Pause.**
6. **Baseline correction.** At this stage, catch up the whole processing for subject 3 and create Figure 4 **Pause.**
7. **Sensor space analysis.** Create Figure 5 for Subject 3 **Pause.** Then iterate for all subjects until this stage (do not recreate figures 1-4) to create Figure 5 on all subjects.
8. **Contrasting conditions and statistics.** Recreate Figure 6 and 7.
9. **Decoding.** A decoding performance figure.
10. **Source space.** Add coreg / BEM / forward / inverse using the «obVdo» Apps locally cloned. One subject, then all. Figure 9 shows coregistration for Subject 3 (?) **Pause.**
11. **Covariance estimation and whitening.** Create Figure 10.
12. **Group source reconstruction.** Create Figure 11
13. **Source space statistics.** Create Figure 12

## Working rules
- Start with S10 run 02, then S03, then all subjects.
- Be explicit about what runs locally (editing App code, Docker builds, GitHub) vs. on the
  Brainlife platform / `bl` CLI (staging data, running the pipeline). Flag platform steps, don't assume.
- Keep a task list and keep the strategy doc current.

## Definition of done
- Target figures reproduced and compared to the paper (written note).
- Refactored Apps forked + published under BrainlifeMEEG, documented and robust.

## Working with me
Check in at each phase boundary and whenever a decision changes scope, cost, or the App graph.
