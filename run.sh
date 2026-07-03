conda init && conda activate buddyme

export BUDDYME_HOME=./vacing/
export BUDDYME_HTTP_DEBUG=1

model_name=deepseek_flash
model_name=glm
model_name=glm-4.5-air
python -m buddyMe --mode $model_name --sub-model $model_name
