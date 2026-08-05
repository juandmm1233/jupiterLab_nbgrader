# Copia el script de inicialización del curso y la tarea de ejemplo
# al workspace del usuario admin (volumen jupyterhub-user-admin).
#
# Uso (PowerShell, desde la raíz del proyecto):
#     .\scripts\seed-instructor.ps1
#     .\scripts\seed-instructor.ps1 -User otroProfesor

param(
    [string]$User = "admin"
)

$ContainerName = "seed-helper-$User"
$VolumeName = "jupyterhub-user-$User"

Write-Host "[i] Sembrando archivos de nbgrader en $VolumeName ..."

# Ignorar error si el contenedor no existe
$null = docker rm -f $ContainerName 2>&1
$ErrorActionPreference = "Stop"

docker run -d --name $ContainerName `
    -v "${VolumeName}:/home/jovyan/work" `
    --user root `
    jupyterlab-singleuser:latest sleep 30 | Out-Null

docker cp .\nbgrader\init-course.sh "${ContainerName}:/home/jovyan/work/init-course.sh"
docker cp .\nbgrader\example-assignment "${ContainerName}:/home/jovyan/work/example-assignment"
docker exec $ContainerName chown -R 1000:100 /home/jovyan/work
docker exec $ContainerName chmod +x /home/jovyan/work/init-course.sh

docker rm -f $ContainerName | Out-Null

Write-Host "[OK] Listo. En la terminal de JupyterLab del profesor ejecuta:"
Write-Host "       bash ~/work/init-course.sh"
