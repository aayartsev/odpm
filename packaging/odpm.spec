# odpm RPM spec — Fedora 40+ (host Python >= 3.10; pyproject PEP 517 macros).
# Version/Release: scripts/build_rpm.sh maps RELEASE_VERSION (e.g. 4.4.2-beta → 4.4.2 + beta).
# ODPM_VERSION aliases RELEASE_VERSION; flat odpm.json contract line stays 4.0 until v2 migrate.

%global srcname odpm
%global version 4.4.2
%global release beta

Name:           %{srcname}
Version:        %{version}
Release:        %{release}%{?dist}
Summary:        Declarative developer environment manager (odpm)
License:        GPL-3.0-or-later
URL:            https://github.com/aayartsev/odpm
Source0:        %{srcname}-%{version}.tar.gz
BuildArch:      noarch

BuildRequires:  python3-devel
BuildRequires:  python3-setuptools
BuildRequires:  python3-wheel
BuildRequires:  python3-packaging
BuildRequires:  python3-jsonschema
BuildRequires:  python3-pluggy

Requires:       python3-packaging
Requires:       python3-jsonschema
Requires:       python3-pluggy
Requires:       git
Recommends:     moby-engine
Recommends:     docker

%description
Declarative environment manager for Odoo development projects.
Reads the odpm project descriptor from a repository and prepares
Docker-based development stacks (clone sources, build images, compose up
PostgreSQL and Odoo).
Host CLI uses PyPI or distribution Python packages for validation and plugins.

%prep
%autosetup -n %{srcname}-%{version}

%generate_buildrequires
%pyproject_buildrequires

%build
%pyproject_wheel

%install
%pyproject_install

%check
# Unit tests live in tests/ at repo root (CI), not inside the installed package.

%files
%license LICENSE
%{_bindir}/odpm
%{python3_sitelib}/dev_project/
%{python3_sitelib}/odpm-*.dist-info/

%changelog
* Sat Jun 21 2026 odpm maintainers <odpm-maintainers@noreply.github.com> - 4.4.2-beta
- Pre-release 4.4.2-beta before stable 4.4.2 (see CHANGELOG.md).
* Sat Jun 20 2026 odpm maintainers <odpm-maintainers@noreply.github.com> - 4.4.2-1
- Patch release 4.4.2 (debt-closure P1-P6; see CHANGELOG.md).
* Mon Jun 08 2026 odpm maintainers <odpm-maintainers@noreply.github.com> - 4.3-rc1
- Pre-release 4.3-rc1. Manifest format odpm_version remains 4.0.
* Mon Jun 08 2026 odpm maintainers <odpm-maintainers@noreply.github.com> - 4.0-1
- Initial RPM package for odpm 4.0 (roadmap 4.3 B2).
