#!/bin/bash

# This script will push files in 
# --project 655fc8c3b094062da64c7e2b \    # project raw data
# --project 640755cac538c16a826b6403   \    # project analysis


# skip this block
if false; then
    in_dir='/home/maximilien.chaumon/liensNet/analyse/BRAINLIFE/code/local_scripts/AggregatedTrialDrop'

    # bl login should have been done already

    # list files in in_dir
    files=`ls $in_dir`

    # push files to bl
    for file in $files
    do
        # from file, extract subject, task, run
        subject=`echo $file | cut -d'_' -f1`
        task=`echo $file | cut -d'_' -f2`
        pass=`echo $file | cut -d'_' -f3 | cut -d'.' -f1`

        # # if task is T2, skip
        # if [ $task == "T2" ]; then
        #     continue
        # fi
        bl data upload \
        --project 655fc8c3b094062da64c7e2b \
        --datatype neuro/meg/fif-override \
        --tag bad-epochs \
        --tag $pass \
        --desc "Bad epochs for $subject $task $pass" \
        --subject $subject \
        --events $in_dir/$file
    done
fi



# now do the same for 
in_dir='/home/maximilien.chaumon/liensNet/analyse/BRAINLIFE/code/local_scripts/AggregatedChannelDrop'
files=`ls $in_dir`
for file in $files
do
    # Skip files with _Face1 and non-.tsv files
    if [[ $file == *"_Face1"* ]] || [[ $file != *.tsv ]]; then
        continue
    fi
    
    # from file, extract subject, task, run
    subject=`echo $file | cut -d'_' -f1`
    task_num=`echo $file | cut -d'_' -f2 | cut -d'.' -f1`
    
    # Convert T1/T2 to Task1/Task2
    if [ "$task_num" == "T1" ]; then
        task="Task1"
    elif [ "$task_num" == "T2" ]; then
        task="Task2"
    else
        task="$task_num"
    fi

    # # if task is T2, skip
    # if [ $task == "T2" ]; then
    #     continue
    # fi
    # verbose files to be uploaded
    echo "### Uploading $file for subject $subject, task $task..."
    bl data upload \
    --project 655fc8c3b094062da64c7e2b \
    --datatype neuro/meg/fif-override \
    --tag bad-channels \
    --tag $task \
    --desc "Bad channels for $subject $task" \
    --subject $subject \
    --channels $in_dir/$file
done