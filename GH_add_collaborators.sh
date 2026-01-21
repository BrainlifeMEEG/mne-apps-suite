# Log in to GitHub as BrainlifeMEEG
gh auth login


# Loop through all repositories of the user BrainlifeMEEG and add collaborators
for repo in $(gh repo list BrainlifeMEEG --json name -q '.[].name'); do
    REPO="BrainlifeMEEG/$repo"
    
    gh api -X PUT -H "Accept: application/vnd.github.v3+json" \
        "/repos/$REPO/collaborators/dnacombo" -f permission=push

    gh api -X PUT -H "Accept: application/vnd.github.v3+json" \
        "/repos/$REPO/collaborators/guiomar" -f permission=push

    gh api -X PUT -H "Accept: application/vnd.github.v3+json" \
        "/repos/$REPO/collaborators/KSalibay" -f permission=push
done