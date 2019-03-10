
# Install Gnucash

On Debian based operating systems:

Install missing packages:

```
aptitude install cmake libxml2 swig
aptitude install libgwengui-gtk2-dev libgwengui-gtk3-dev
aptitude install libwebkitgtk-dev libwebkit2gtk-4.0-dev
aptitude install guile-2.2-dev
aptitude install libaqbanking-dev libofx-dev
aptitude install libdbi-dev libdbd-sqlite3
aptitude install libsecret-1-dev
aptitude install libboost-chrono-dev libboost-date-time-dev libboost-filesystem-dev libboost-log-dev libboost-program-options-dev libboost-regex-dev libboost-signals-dev libboost-system-dev libboost-test-dev libboost-locale-dev 
aptitude install googletest
aptitude install google-mock
aptitude install googletest-tools
```

Compile Gnucash

```
git clone --depth 100 https://github.com/Gnucash/gnucash.git
cd gnucash
GC=$(realpath .)
mkdir build-3.4
cd build-3.4
cmake -DWITH_PYTHON=ON  -DCMAKE_INSTALL_PREFIX=$GC/install-3.4/ -DCMAKE_PREFIX_PATH=$GC/install-3.4/ -DGTEST_ROOT=/usr/src/googletest/googletest/ -DGMOCK_ROOT=/usr/src/gmock/ ../

make -j4
make install

```

