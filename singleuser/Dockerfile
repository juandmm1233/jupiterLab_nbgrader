FROM quay.io/jupyter/scipy-notebook:2024-12-23

USER root

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        git \
        curl \
        ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Crea el punto de montaje del exchange con permisos correctos.
# Cuando docker monte el volumen nombrado encima, Docker copia estos
# permisos al volumen vacío en su primer uso.
RUN mkdir -p /srv/nbgrader/exchange \
    && chown -R ${NB_UID}:${NB_GID} /srv/nbgrader \
    && chmod -R 0755 /srv/nbgrader

# Instalación de paquetes Python como jovyan (es lo que hace el base image)
USER ${NB_UID}

RUN pip install --no-cache-dir \
        nbgitpuller==1.2.2 \
        jupyterhub==5.2.* \
        jupyterlab-git==0.50.* \
        nbgrader==0.9.5

# Habilita las extensiones de nbgrader a nivel SISTEMA -> requiere root
# para escribir en /usr/local/etc/jupyter. Las extensiones del lado servidor
# y frontend son visibles para todos, pero el Formgrader/Create-Assignment
# se autoocultan para no-instructores gracias a JupyterHubAuthPlugin.
USER root

RUN jupyter labextension enable --level=system nbgrader:formgrader \
                                                nbgrader:assignment-list \
                                                nbgrader:create-assignment \
                                                nbgrader:course-list \
 && jupyter server extension enable --system nbgrader.server_extensions.formgrader \
                                              nbgrader.server_extensions.assignment_list \
                                              nbgrader.server_extensions.course_list \
                                              nbgrader.server_extensions.validate_assignment

COPY --chown=${NB_UID}:${NB_GID} nbgrader_config.py /etc/jupyter/nbgrader_config.py
COPY --chown=${NB_UID}:${NB_GID} requirements.txt /tmp/requirements.txt

USER ${NB_UID}

RUN if [ -s /tmp/requirements.txt ]; then \
        pip install --no-cache-dir -r /tmp/requirements.txt; \
    fi

WORKDIR /home/jovyan/work
EXPOSE 8888
