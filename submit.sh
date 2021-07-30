#!/bin/bash
#
#BATCH --job-name=exp_krish31
#
#SBATCH --time=48:00:00
#SBATCH --ntasks=1
#SBATCH -p gpu
#SBATCH --gres=gpu:1
#SBATCH -C GPU_MEM:32GB
#SBATCH -e /scratch/groups/rubin/krish05m/AttentionMap/saved_batches/exp_krish31.err
#SBATCH -o /scratch/groups/rubin/krish05m/AttentionMap/saved_batches/exp_krish31.out
export BATCH_DIRECTORY=exp_krish31
export LEARNING_RATE=0.000005
export NUM_EPOCHS=10
export BATCH_SIZE=4
export RESOLUTION_MATCH=4
export SIMILARITY_METRIC=1
export ALPHA=8

mkdir /scratch/groups/rubin/krish05m/AttentionMap/saved_batches/$BATCH_DIRECTORY
ml python/3.9.0
ml opencv/4.5.2

python3 main.py loadCheckpoint visualLoss train noTrackLoss supervised $BATCH_DIRECTORY $LEARNING_RATE $NUM_EPOCHS $BATCH_SIZE $RESOLUTION_MATCH $SIMILARITY_METRIC $ALPHA