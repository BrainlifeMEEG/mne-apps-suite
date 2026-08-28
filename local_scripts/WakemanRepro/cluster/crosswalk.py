"""
openfMRI subject_id (the mne-biomag-group-demo scripts' own indexing key,
"sub%03d") <-> BIDS subject ("sub-NN") crosswalk for ds000117.

Source: ds000117's own README table, reproduced in full with justification
in the Step 0 plan (~/.claude/plans/jazzy-swinging-whistle.md) and in
original_scripts/GLITCHES.md. Reproduced here as data so cluster tooling
doesn't have to re-derive it.

VERIFICATION STATUS: only openfMRI id 10 (BIDS sub-09, our "S09") has been
independently verified -- its per-run EEG bad-channel count was checked
against the paper's own published Figure 2. Every other row rests on the
README table alone; the crosswalk cross-check strategy for those (Stage 1
count-screen / Stage 2 name-match, see the plan) has NOT been run yet.
Treat any pipeline output for a subject other than 10 as provisional until
that cross-check happens.
"""

# openfMRI subject_id -> BIDS subject id
OPENFMRI_TO_BIDS = {
    2: "sub-01",
    3: "sub-02",
    4: "sub-03",
    6: "sub-05",
    7: "sub-06",
    8: "sub-07",
    9: "sub-08",
    10: "sub-09",   # verified against paper Figure 2 -- our "S09"
    11: "sub-04",
    12: "sub-10",
    13: "sub-11",
    14: "sub-12",
    15: "sub-13",
    17: "sub-14",
    18: "sub-15",
    19: "sub-16",
}

# Excluded per ds000117's README (bad EEG / poor EEG-fMRI quality) --
# matches library/config.py's own exclude_subjects = [1, 5, 16].
EXCLUDED = {1, 5, 16}

VERIFIED = {10}

ALL_SUBJECT_IDS = sorted(OPENFMRI_TO_BIDS)


def bids_id(openfmri_subject_id):
    if openfmri_subject_id in EXCLUDED:
        raise ValueError(
            f"openfMRI subject_id {openfmri_subject_id} is excluded per "
            f"ds000117's README / config.py's exclude_subjects -- not in "
            f"the crosswalk on purpose."
        )
    try:
        return OPENFMRI_TO_BIDS[openfmri_subject_id]
    except KeyError:
        raise ValueError(
            f"openfMRI subject_id {openfmri_subject_id} is not a known "
            f"ds000117 subject (valid: {ALL_SUBJECT_IDS})"
        )
