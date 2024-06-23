# LAWN STATS App<a name="lawn-stats-app"></a>

Description of app

![License](https://img.shields.io/badge/license-GPLv3-green)
![python](https://img.shields.io/badge/python-3.8-informational)
![django](https://img.shields.io/badge/django-3.2-informational)
![pre-commit](https://img.shields.io/badge/pre--commit-enabled-brightgreen?logo=pre-commit&logoColor=white)

_(These badges are examples, you can and should replace them with your own)_

______________________________________________________________________

<!-- mdformat-toc start --slug=github --maxlevel=6 --minlevel=1 -->

- [LAWN STATS App](#lawn-stats-app)
  - [Installing into production AA](#installing-into-production-aa)
  - [Optional Settings](#optional-settings)
  - [Permissions](#permissions)

<!-- mdformat-toc end -->

## Installing into production AA<a name="installing-into-production-aa"></a>

To install your plugin into a production AA run this command within the virtual Python environment of your AA installation:

```bash
pip install git+https://github.com/swashman/lawn-stats
```

- Add `'lawn_stats',` to `INSTALLED_APPS` in `settings/local.py`
- add the following settings to `settings/local.py`

```python
## base plugin SETTINGS
SOME_SETTING = "setting"
```

- run migrations
- restart your allianceserver.

## Optional Settings<a name="optional-settings"></a>

| Setting            | Default | Description                          |
| :----------------- | :------ | :----------------------------------- |
| `OPTIONAL_SETTING` | `True`  | some optional setting does something |

## Permissions<a name="permissions"></a>

| ID             | Description           | Notes                   |
| :------------- | :-------------------- | :---------------------- |
| `basic_access` | Can access the module | basic access permission |
