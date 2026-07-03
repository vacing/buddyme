conda activate buddyme
model_name=deepseek_flash
model_name=glm
export BUDDYME_HOME=~/cloud_code/vacing/
python -m buddyMe --mode $model_name --sub-model $model_name
