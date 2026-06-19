# odpm RPM spec — Fedora 40+ (host Python >= 3.10; pyproject PEP 517 macros).
# Version/Release track dev_project.constants.RELEASE_VERSION (currently 4.4.0-alpha).
# ODPM_VERSION (4.4) is the manager line; flat odpm.json contract line stays 4.0 until v2 migrate.

%global srcname odpm

Name:           %{srcname}
Version:        4.4
Release:        0.alpha%{?dist}
Summary:        Declarative developer environment manager (odpm)
License:        GPL-3.0-or-later
URL:            https://github.com/aayartsev/odpm
Source0:        %{srcname}-%{version}.tar.gz
BuildArch:      noarch

BuildRequires:  python3-devel
BuildRequires:  python3-setuptools
BuildRequires:  python3-wheel
BuildRequires:  python3-packaging

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
PostgreSQL and Odoo). Host CLI uses jsonschema and pluggy (PyPI or distro packages).

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
* Mon Jun 08 2026 odpm maintainers <odpm-maintainers@noreply.github.com> - 4.3-rc1
- Pre-release 4.3-rc1. Manifest format odpm_version remains 4.0.
* Mon Jun 08 2026 odpm maintainers <odpm-maintainers@noreply.github.com> - 4.0-1
- Initial RPM package for odpm 4.0 (roadmap 4.3 B2).
