FROM quay.io/jupyter/scipy-notebook:2024-12-23

USER root

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        git \
        curl \
        ca-certificates \
    && rm -rf /var/lib/apt/lists/*

USER ${NB_UID}

RUN pip install --no-cache-dir \
        nbgitpuller==1.2.2 \
        jupyterhub==5.2.* \
        jupyterlab-git==0.50.* \
    && jupyter labextension list

COPY --chown=${NB_UID}:${NB_GID} requirements.txt /tmp/requirements.txt
RUN if [ -s /tmp/requirements.txt ]; then \
        pip install --no-cache-dir -r /tmp/requirements.txt; \
    fi

WORKDIR /home/jovyan/work
EXPOSE 8888
