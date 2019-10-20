export PYTHONPATH="/home/tr/software/gnucash/install-3.7/lib/python3.7/site-packages"
DIR="$(dirname "$(readlink -f "$0")")"

echo $DIR

python3 $DIR/main.py "$@"

