set -e
E=/root/news_2026-09-23_env
mkdir -p $E
export UV_CACHE_DIR=$E/.uvcache UV_PYTHON_INSTALL_DIR=$E/.uvpy
python3 -m venv $E/uvboot
$E/uvboot/bin/pip -q install uv
$E/uvboot/bin/uv python install 3.14.4
$E/uvboot/bin/uv venv --python 3.14.4 $E/venv314
$E/uvboot/bin/uv pip install --python $E/venv314/bin/python lightgbm==4.7.0 narwhals==2.24.0 numpy==2.5.2 pandas==3.0.5 python-dateutil==2.9.0.post0 scipy==1.18.0 six==1.17.0
rm -rf $E/.uvcache
$E/venv314/bin/python -c "import sys,numpy,scipy,pandas,lightgbm; print(sys.version); print(numpy.__version__, scipy.__version__, pandas.__version__, lightgbm.__version__)"
du -sh $E
echo VENV_DONE
