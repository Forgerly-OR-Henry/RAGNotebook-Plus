#!/usr/bin/env bash

# CentOS/RHEL 用户快捷管理脚本
# 用法：sudo bash centos-user-manager.sh

set -o pipefail

SUDO_GROUP="wheel"
DEFAULT_SHELL="/bin/bash"

init_style() {
  if [[ -t 1 ]] && command -v tput >/dev/null 2>&1; then
    BOLD="$(tput bold 2>/dev/null || true)"
    DIM="$(tput dim 2>/dev/null || true)"
    RED="$(tput setaf 1 2>/dev/null || true)"
    GREEN="$(tput setaf 2 2>/dev/null || true)"
    YELLOW="$(tput setaf 3 2>/dev/null || true)"
    BLUE="$(tput setaf 4 2>/dev/null || true)"
    CYAN="$(tput setaf 6 2>/dev/null || true)"
    RESET="$(tput sgr0 2>/dev/null || true)"
  else
    BOLD=""
    DIM=""
    RED=""
    GREEN=""
    YELLOW=""
    BLUE=""
    CYAN=""
    RESET=""
  fi
}

say_ok() {
  echo "${GREEN}[完成]${RESET} $*"
}

say_info() {
  echo "${CYAN}[信息]${RESET} $*"
}

say_warn() {
  echo "${YELLOW}[注意]${RESET} $*"
}

say_error() {
  echo "${RED}[错误]${RESET} $*" >&2
}

require_root() {
  if [[ "${EUID}" -ne 0 ]]; then
    say_error "请使用 root 权限运行，例如：sudo bash $0"
    exit 1
  fi
}

screen_clear() {
  if [[ -t 1 ]]; then
    clear
  fi
}

pause() {
  echo
  read -r -p "按 Enter 返回主菜单..."
}

confirm() {
  local prompt="$1"
  local answer
  local yes_pattern='^([Yy]|[Yy][Ee][Ss])$'
  read -r -p "${prompt} [y/N]: " answer
  [[ "${answer}" =~ ${yes_pattern} ]]
}

valid_new_username() {
  [[ "$1" =~ ^[a-z_][a-z0-9_-]{0,31}$ ]]
}

read_new_username() {
  local username
  while true; do
    read -r -p "请输入要创建的用户名: " username
    if [[ -z "${username}" ]]; then
      say_error "用户名不能为空。"
    elif ! valid_new_username "${username}"; then
      say_error "用户名需为 1-32 位：小写字母、数字、下划线、短横线；开头必须是小写字母或下划线。"
    elif id "${username}" >/dev/null 2>&1; then
      say_error "用户 '${username}' 已存在。"
    else
      printf '%s\n' "${username}"
      return 0
    fi
  done
}

read_existing_username() {
  local prompt="${1:-请输入用户名: }"
  local username
  while true; do
    read -r -p "${prompt}" username
    if [[ -z "${username}" ]]; then
      say_error "用户名不能为空。"
    elif ! id "${username}" >/dev/null 2>&1; then
      say_error "用户 '${username}' 不存在。"
    else
      printf '%s\n' "${username}"
      return 0
    fi
  done
}

protect_builtin_user() {
  local username="$1"
  case "${username}" in
    root|bin|daemon|adm|lp|sync|shutdown|halt|mail|operator|games|ftp|nobody)
      say_error "为避免误操作，拒绝修改系统内置用户：${username}"
      return 1
      ;;
  esac
  return 0
}

ensure_sudo_group() {
  if ! getent group "${SUDO_GROUP}" >/dev/null 2>&1; then
    say_warn "sudo 用户组 '${SUDO_GROUP}' 不存在，正在创建..."
    groupadd "${SUDO_GROUP}" || return 1
  fi
}

show_result() {
  local exit_code="$1"
  local success_msg="$2"
  local failed_msg="$3"
  if [[ "${exit_code}" -eq 0 ]]; then
    say_ok "${success_msg}"
  else
    say_error "${failed_msg}"
  fi
}

create_user() {
  local username
  username="$(read_new_username)"

  say_info "正在创建用户 '${username}'..."
  if ! useradd -m -s "${DEFAULT_SHELL}" "${username}"; then
    say_error "创建用户 '${username}' 失败。"
    return 1
  fi

  echo
  say_info "请为 '${username}' 设置登录密码："
  passwd "${username}"

  if confirm "是否授予 '${username}' sudo 权限"; then
    ensure_sudo_group && usermod -aG "${SUDO_GROUP}" "${username}"
    show_result "$?" "已通过 '${SUDO_GROUP}' 组授予 sudo 权限。" "授予 sudo 权限失败。"
  fi

  say_ok "用户 '${username}' 创建完成。"
}

delete_user() {
  local username
  username="$(read_existing_username "请输入要删除的用户名: ")"
  protect_builtin_user "${username}" || return 1

  echo
  say_warn "即将删除用户：${username}"
  if ! confirm "确认继续删除"; then
    say_info "已取消。"
    return 0
  fi

  if confirm "是否同时删除 home 目录和邮件文件"; then
    userdel -r "${username}"
  else
    userdel "${username}"
  fi
  show_result "$?" "用户 '${username}' 已删除。" "删除用户 '${username}' 失败。"
}

reset_password() {
  local username
  username="$(read_existing_username "请输入要重置密码的用户名: ")"
  protect_builtin_user "${username}" || return 1
  passwd "${username}"
}

lock_user() {
  local username
  username="$(read_existing_username "请输入要锁定的用户名: ")"
  protect_builtin_user "${username}" || return 1
  passwd -l "${username}"
  show_result "$?" "用户 '${username}' 已锁定。" "锁定用户 '${username}' 失败。"
}

unlock_user() {
  local username
  username="$(read_existing_username "请输入要解锁的用户名: ")"
  protect_builtin_user "${username}" || return 1
  passwd -u "${username}"
  show_result "$?" "用户 '${username}' 已解锁。" "解锁用户 '${username}' 失败。"
}

grant_sudo() {
  local username
  username="$(read_existing_username "请输入要授予 sudo 的用户名: ")"
  protect_builtin_user "${username}" || return 1
  ensure_sudo_group && usermod -aG "${SUDO_GROUP}" "${username}"
  show_result "$?" "已通过 '${SUDO_GROUP}' 组授予 sudo 权限。" "授予 sudo 权限失败。"
}

revoke_sudo() {
  local username
  username="$(read_existing_username "请输入要撤销 sudo 的用户名: ")"
  protect_builtin_user "${username}" || return 1

  if id -nG "${username}" | tr ' ' '\n' | grep -Fxq "${SUDO_GROUP}"; then
    gpasswd -d "${username}" "${SUDO_GROUP}"
    show_result "$?" "已从 '${SUDO_GROUP}' 组移除 '${username}'。" "撤销 sudo 权限失败。"
  else
    say_info "用户 '${username}' 当前不在 '${SUDO_GROUP}' 组中。"
  fi
}

show_user() {
  local username
  username="$(read_existing_username "请输入要查看的用户名: ")"

  echo
  echo "${BOLD}${BLUE}基本信息${RESET}"
  id "${username}"

  echo
  echo "${BOLD}${BLUE}密码状态${RESET}"
  passwd -S "${username}" 2>/dev/null || say_warn "当前系统不支持 passwd -S 输出。"

  echo
  echo "${BOLD}${BLUE}账号有效期${RESET}"
  chage -l "${username}" 2>/dev/null || say_warn "当前系统不支持 chage -l 输出。"
}

list_users() {
  echo "${BOLD}${BLUE}普通用户列表${RESET}"
  printf '%-24s %-8s %-8s %-30s %s\n' "用户名" "UID" "GID" "HOME目录" "Shell"
  printf '%-24s %-8s %-8s %-30s %s\n' "------------------------" "--------" "--------" "------------------------------" "----------------"
  awk -F: '($3 == 0 || ($3 >= 1000 && $3 < 60000)) {
    printf "%-24s %-8s %-8s %-30s %s\n", $1, $3, $4, $6, $7
  }' /etc/passwd
}

expire_password() {
  local username
  username="$(read_existing_username "请输入要强制改密的用户名: ")"
  protect_builtin_user "${username}" || return 1
  chage -d 0 "${username}"
  show_result "$?" "用户 '${username}' 下次登录时必须修改密码。" "设置失败。"
}

add_ssh_key() {
  local username home group key auth_keys
  username="$(read_existing_username "请输入要添加 SSH 公钥的用户名: ")"
  protect_builtin_user "${username}" || return 1

  home="$(getent passwd "${username}" | cut -d: -f6)"
  group="$(id -gn "${username}")"

  if [[ -z "${home}" ]]; then
    say_error "无法获取用户 '${username}' 的 home 目录。"
    return 1
  fi

  echo
  read -r -p "请粘贴 SSH 公钥: " key
  if [[ -z "${key}" ]]; then
    say_error "SSH 公钥不能为空。"
    return 1
  fi

  install -d -m 700 -o "${username}" -g "${group}" "${home}/.ssh"
  auth_keys="${home}/.ssh/authorized_keys"
  touch "${auth_keys}"
  chown "${username}:${group}" "${auth_keys}"
  chmod 600 "${auth_keys}"

  if grep -Fxq "${key}" "${auth_keys}"; then
    say_info "该公钥已经存在，无需重复添加。"
  else
    printf '%s\n' "${key}" >> "${auth_keys}"
    say_ok "SSH 公钥已添加到 ${auth_keys}。"
  fi
}

print_header() {
  local host current_user
  host="$(hostname 2>/dev/null || echo unknown)"
  current_user="$(whoami 2>/dev/null || echo root)"

  echo "${BOLD}${CYAN}+------------------------------------------------------------+${RESET}"
  echo "${BOLD}${CYAN}|                    CentOS 用户管理工具                    |${RESET}"
  echo "${BOLD}${CYAN}+------------------------------------------------------------+${RESET}"
  echo "${DIM}主机: ${host}    当前用户: ${current_user}    sudo组: ${SUDO_GROUP}${RESET}"
  echo
}

print_menu() {
  screen_clear
  print_header
  echo "${BOLD}${BLUE}[用户管理]${RESET}"
  echo "  1) 创建用户"
  echo "  2) 删除用户"
  echo "  3) 查看用户详情"
  echo "  4) 列出普通用户"
  echo
  echo "${BOLD}${BLUE}[密码与登录]${RESET}"
  echo "  5) 重置密码"
  echo "  6) 锁定用户"
  echo "  7) 解锁用户"
  echo "  8) 强制下次登录修改密码"
  echo "  9) 添加 SSH 公钥"
  echo
  echo "${BOLD}${BLUE}[sudo 权限]${RESET}"
  echo " 10) 授予 sudo 权限"
  echo " 11) 撤销 sudo 权限"
  echo
  echo "${BOLD}  0) 退出${RESET}"
  echo
}

main() {
  local choice
  init_style
  require_root

  while true; do
    print_menu
    read -r -p "请选择操作编号: " choice
    echo
    case "${choice}" in
      1) create_user; pause ;;
      2) delete_user; pause ;;
      3) show_user; pause ;;
      4) list_users; pause ;;
      5) reset_password; pause ;;
      6) lock_user; pause ;;
      7) unlock_user; pause ;;
      8) expire_password; pause ;;
      9) add_ssh_key; pause ;;
      10) grant_sudo; pause ;;
      11) revoke_sudo; pause ;;
      0) say_info "已退出。"; exit 0 ;;
      *) say_error "无效选项，请重新输入。"; pause ;;
    esac
  done
}

main "$@"
