GENCCODE_ASSEMBLY_TYPE=-a gcc
SO=so
SOBJ=so
A=a
LIBPREFIX=lib
LIB_EXT_ORDER=.78.2
COMPILE=/home/conda/feedstock_root/build_artifacts/icu_1767969498351/_build_env/bin/x86_64-conda-linux-gnu-cc -DNDEBUG -D_FORTIFY_SOURCE=2 -O2 -isystem /users/sc23ksk/nonaga-algorithm/conda_env/include -D_REENTRANT  -DU_HAVE_ELF_H=1  -DU_ALL_IMPLEMENTATION -DU_ATTRIBUTE_DEPRECATED= -march=nocona -mtune=haswell -ftree-vectorize -fPIC -fstack-protector-strong -fno-plt -O2 -ffunction-sections -pipe -isystem /users/sc23ksk/nonaga-algorithm/conda_env/include -fdebug-prefix-map=/home/conda/feedstock_root/build_artifacts/icu_1767969498351/work=/usr/local/src/conda/icu-78.2 -fdebug-prefix-map=/users/sc23ksk/nonaga-algorithm/conda_env=/usr/local/src/conda-prefix -std=c11 -Wall -pedantic -Wshadow -Wpointer-arith -Wmissing-prototypes -Wwrite-strings   -c
LIBFLAGS=-I/users/sc23ksk/nonaga-algorithm/conda_env/include -DPIC -fPIC
GENLIB=/home/conda/feedstock_root/build_artifacts/icu_1767969498351/_build_env/bin/x86_64-conda-linux-gnu-cc -march=nocona -mtune=haswell -ftree-vectorize -fPIC -fstack-protector-strong -fno-plt -O2 -ffunction-sections -pipe -isystem /users/sc23ksk/nonaga-algorithm/conda_env/include -fdebug-prefix-map=/home/conda/feedstock_root/build_artifacts/icu_1767969498351/work=/usr/local/src/conda/icu-78.2 -fdebug-prefix-map=/users/sc23ksk/nonaga-algorithm/conda_env=/usr/local/src/conda-prefix -std=c11 -Wall -pedantic -Wshadow -Wpointer-arith -Wmissing-prototypes -Wwrite-strings   -Wl,-O2 -Wl,--sort-common -Wl,--as-needed -Wl,-z,relro -Wl,-z,now -Wl,--disable-new-dtags -Wl,--gc-sections -Wl,--allow-shlib-undefined -Wl,-rpath,/users/sc23ksk/nonaga-algorithm/conda_env/lib -Wl,-rpath-link,/users/sc23ksk/nonaga-algorithm/conda_env/lib -L/users/sc23ksk/nonaga-algorithm/conda_env/lib  -shared -Wl,-Bsymbolic
LDICUDTFLAGS=-nodefaultlibs -nostdlib
LD_SONAME=-Wl,-soname -Wl,
RPATH_FLAGS=
BIR_LDFLAGS=-Wl,-Bsymbolic
AR=/home/conda/feedstock_root/build_artifacts/icu_1767969498351/_build_env/bin/x86_64-conda-linux-gnu-ar
ARFLAGS=r
RANLIB=/home/conda/feedstock_root/build_artifacts/icu_1767969498351/_build_env/bin/x86_64-conda-linux-gnu-ranlib
INSTALL_CMD=/usr/bin/install -c
