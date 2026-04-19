pkgname=howdy-gesture-tfg
pkgver=0.1.0.r39.g020407f
pkgrel=1
pkgdesc="Howdy + gesture authentication layer (TFG)"
arch=('x86_64')
url="https://github.com/Palm-Pass/tfg"
license=('MIT')
install="${pkgname}.install"
depends=(
  'pam'
  'dbus'
  'python'
  'libevdev'
  'libinih'
)
makedepends=(
  'gcc'
  'git'
  'pkgconf'
  'meson'
  'ninja'
)
source=(
  "tfg::git+https://github.com/Palm-Pass/tfg.git#branch=main"
  "howdy::git+https://github.com/boltgolt/howdy.git#commit=d3ab99382f88f043d15f15c1450ab69433892a1c"
)
sha256sums=('SKIP' 'SKIP')

pkgver() {
  cd "${srcdir}/tfg"
  printf '0.1.0.r%s.g%s' "$(git rev-list --count HEAD)" "$(git rev-parse --short HEAD)"
}

prepare() {
  cd "${srcdir}/tfg"

  rm -rf external/howdy
  cp -a "${srcdir}/howdy" external/howdy

  python3 - << 'PY'
from pathlib import Path

pam_main = Path("external/howdy/howdy/src/pam/main.cc")
source = pam_main.read_text()

old = '''  const char *const args[] = {PYTHON_EXECUTABLE_PATH, // NOLINT
                              COMPARE_PROCESS_PATH, username, nullptr};
  pid_t child_pid;

  // Start the python subprocess
  if (posix_spawnp(&child_pid, PYTHON_EXECUTABLE_PATH, nullptr, nullptr,
                   const_cast<char *const *>(args), nullptr) != 0) {
'''

new = '''  const char *const args[] = {COMPARE_PROCESS_PATH, username, nullptr};
  pid_t child_pid;

  // Start the compare subprocess (script shebang decides Python executable)
  if (posix_spawnp(&child_pid, COMPARE_PROCESS_PATH, nullptr, nullptr,
                   const_cast<char *const *>(args), nullptr) != 0) {
'''

if old not in source:
    raise SystemExit("Failed to patch pam main.cc: expected block not found")

pam_main.write_text(source.replace(old, new, 1))
PY
}

build() {
  cd "${srcdir}/tfg/external/howdy"

  meson setup build \
    --prefix=/usr \
    --libdir=lib \
    --sysconfdir=etc \
    -Dpython_path=/usr/bin/python3 \
    -Dconfig_dir=/etc/howdy \
    -Ddlib_data_dir=/usr/share/dlib-data \
    -Duser_models_dir=/etc/howdy/models \
    -Dlog_path=/var/log/howdy \
    -Dinstall_pam_config=false \
    -Dwith_polkit=false

  meson compile -C build

  cd "${srcdir}/tfg"
  gcc -fPIC -fno-stack-protector -Wall -c src/pam_gesture.c -o "${srcdir}/pam_gesture.o"
  ld -x --shared -o "${srcdir}/pam_gesture.so" "${srcdir}/pam_gesture.o" -lpam

  gcc src/dbus_notification.c -o "${srcdir}/dbus_notification" $(pkg-config --cflags --libs dbus-1)
}

package() {
  local repo="${srcdir}/tfg"
  local local_src_dir="${startdir}/src"
  local root="${pkgdir}/usr/lib/howdy"
  local model_src=""

  cd "${srcdir}/tfg/external/howdy"
  meson install -C build --destdir "${pkgdir}"

  install -d "${pkgdir}/etc/howdy"
  install -d "${pkgdir}/etc/howdy/models"
  install -d "${pkgdir}/var/log/howdy"
  install -d "${root}/models"

  install -m 644 "${repo}/external/howdy/howdy/src/config.ini" "${pkgdir}/etc/howdy/config.ini"

  if [[ ! -d "${local_src_dir}" ]]; then
    local_src_dir="${repo}/src"
  fi

  install -m 755 "${local_src_dir}/compare.py" "${root}/compare.py"

  cat > "${pkgdir}/usr/bin/howdy" << 'EOF'
#!/usr/bin/env bash
set -euo pipefail

python_bin="/usr/lib/howdy/.venv/bin/python"
if [[ ! -x "${python_bin}" ]]; then
  python_bin="/usr/bin/python3"
fi

exec "${python_bin}" /usr/lib/howdy/cli.py "$@"
EOF
  chmod 755 "${pkgdir}/usr/bin/howdy"

  install -m 755 "${local_src_dir}/gesture-config.py" "${pkgdir}/usr/bin/howdy-gesture-config"
  install -m 755 "${local_src_dir}/gesture-only.py" "${pkgdir}/usr/bin/howdy-gesture-only"

  for candidate in \
    "${repo}/notebooks/rock_exported_model/gesture_recognizer.task" \
    "${startdir}/notebooks/rock_exported_model/gesture_recognizer.task" \
    "${startdir}/rock_exported_model/gesture_recognizer.task"; do
    if [[ -f "${candidate}" ]]; then
      model_src="${candidate}"
      break
    fi
  done

  if [[ -n "${model_src}" ]]; then
    install -m 644 "${model_src}" "${root}/models/gesture_recognizer.task"
  else
    printf '%s\n' "warning: gesture_recognizer.task not found; install it manually in /usr/lib/howdy/models/" >&2
  fi

  install -m 755 "${srcdir}/dbus_notification" "${root}/dbus_notification"
  install -m 644 "${srcdir}/pam_gesture.so" "${pkgdir}/usr/lib/security/pam_gesture.so"
  install -m 644 "${startdir}/requirements-py310.txt" "${root}/requirements-py310.txt"
}
