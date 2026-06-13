# odpm RPM spec — Fedora 41+ (pyproject PEP 517 macros).
# Version/Release track dev_project.constants.RELEASE_VERSION (currently 4.3-rc1).
# ODPM_VERSION (4.0) is the odpm.json manifest line, not the package release.

%global srcname odpm

Name:           %{srcname}
Version:        4.3
Release:        rc1%{?dist}
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
Requires:       git
Recommends:     moby-engine
Recommends:     docker

%description
Declarative environment manager for Odoo development projects.
Reads the odpm project descriptor from a repository and prepares
Docker-based development stacks (clone sources, build images, compose up
PostgreSQL and Odoo). Zero PyPI runtime dependencies.

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
