pkgname=howdy-gesture-tfg
pkgver=0.1.0
pkgrel=1
pkgdesc="Howdy mod with gesture authentication (TFG)"
arch=('x86_64')
url="https://github.com/Palm-Pass/tfg"
license=('MIT')
install="${pkgname}.install"
depends=(
  'pam'
  'dbus'
)
makedepends=(
  'gcc'
  'git'
  'pkgconf'
)
source=(
  "tfg::git+https://github.com/Palm-Pass/tfg.git#branch=main"
)
sha256sums=('SKIP')

pkgver() {
  cd "${srcdir}/tfg"
  printf '0.1.0.r%s.g%s' "$(git rev-list --count HEAD)" "$(git rev-parse --short HEAD)"
}

prepare() {
  cd "${srcdir}/tfg"
  git submodule update --init --recursive
}

build() {
  cd "${srcdir}/tfg"

  gcc -fPIC -fno-stack-protector -Wall -c src/pam_gesture.c -o "${srcdir}/pam_gesture.o"
  ld -x --shared -o "${srcdir}/pam_gesture.so" "${srcdir}/pam_gesture.o" -lpam

  gcc src/dbus_notification.c -o "${srcdir}/dbus_notification" $(pkg-config --cflags --libs dbus-1)
}

package() {
  local root="${pkgdir}/usr/lib/howdy-gesture"
  local repo="${srcdir}/tfg"

  install -d "${root}"
  install -d "${root}/src"
  install -d "${root}/config"
  install -d "${root}/models"
  install -d "${root}/logs"
  install -d "${root}/external/howdy/howdy/src"
  install -d "${root}/external/howdy/howdy/data"
  install -d "${pkgdir}/usr/lib/security"

  install -m 755 "${repo}/src/compare.py" "${root}/src/compare.py"
  install -m 755 "${repo}/src/gesture-config.py" "${root}/src/gesture-config.py"
  install -m 755 "${repo}/src/gesture-only.py" "${root}/src/gesture-only.py"
  cp -a "${repo}/external/howdy/howdy/src/." "${root}/external/howdy/howdy/src/"
  cp -a "${repo}/external/howdy/howdy/data/." "${root}/external/howdy/howdy/data/"

  install -m 644 "${repo}/external/howdy/howdy/src/config.ini" "${root}/config/config.ini"
  install -m 644 "${repo}/notebooks/rock_exported_model/gesture_recognizer.task" "${root}/models/gesture_recognizer.task"

  install -m 755 "${srcdir}/dbus_notification" "${root}/src/dbus_notification"
  install -m 644 "${srcdir}/pam_gesture.so" "${pkgdir}/usr/lib/security/pam_gesture.so"
  install -m 644 "${repo}/requirements-py310.txt" "${root}/requirements-py310.txt"

  install -d "${pkgdir}/usr/bin"
  install -m 755 "${repo}/src/gesture-config.py" "${pkgdir}/usr/bin/howdy-gesture-config"
  install -m 755 "${repo}/src/gesture-only.py" "${pkgdir}/usr/bin/howdy-gesture-only"
}
