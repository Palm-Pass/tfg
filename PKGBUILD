pkgname=howdy-gesture-tfg
pkgver=0.1.0.r39.g020407f
pkgrel=1
pkgdesc="Howdy + gesture authentication layer (TFG)"
arch=('x86_64')
url="https://github.com/Palm-Pass/tfg"
license=('MIT')
install="${pkgname}.install"
depends=(
  'howdy'
  'pam'
  'dbus'
  'uv'
  'python'
  'libevdev'
  'libinih'
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
}

build() {
  cd "${srcdir}/tfg"
  gcc -fPIC -fno-stack-protector -Wall -c src/pam_gesture.c -o "${srcdir}/pam_gesture.o"
  ld -x --shared -o "${srcdir}/pam_gesture.so" "${srcdir}/pam_gesture.o" -lpam

  gcc src/dbus_notification.c -o "${srcdir}/dbus_notification" $(pkg-config --cflags --libs dbus-1)
}

package() {
  local repo="${srcdir}/tfg"
  local root="${pkgdir}/usr/lib/howdy"

  install -d "${root}/models"

  install -m 755 "${repo}/src/compare.py" "${root}/compare-gesture.py"
  install -m 755 "${repo}/src/gesture-config.py" "${pkgdir}/usr/bin/howdy-gesture-config"
  install -m 755 "${repo}/src/gesture-only.py" "${pkgdir}/usr/bin/howdy-gesture-only"

  install -m 644 "${repo}/models/gesture_recognizer.task" "${root}/models/gesture_recognizer.task"
  install -m 644 "${repo}/pyproject.toml" "${root}/pyproject.toml"
  install -m 644 "${repo}/uv.lock" "${root}/uv.lock"

  install -m 755 "${srcdir}/dbus_notification" "${root}/dbus_notification"
  install -m 644 "${srcdir}/pam_gesture.so" "${pkgdir}/usr/lib/security/pam_gesture.so"
}
