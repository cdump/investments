# Investments
Библиотека для анализа брокерских отчетов + утилита для подготовки налоговой отчетности

![Tests status](https://github.com/cdump/investments/workflows/tests/badge.svg)

## Установка/обновление
```
$ pip install investments --upgrade --user
```
или с помощью [poetry](https://python-poetry.org/)

## Утилита ibtax
Расчет прибыли Interactive Brokers для уплаты налогов для резидентов РФ

- расчет сделок по методу ФИФО, учет даты расчетов (settle date)
- конвертация по курсу ЦБ
- раздельный результат сделок по акциям и опционам + дивиденды
- учёт начисленных процентов на остаток по счету
- пока **НЕ** учитывает комисии по сделкам (т.е. налог будет немного больше, в пользу налоговой)
- пока **НЕ** поддерживаются сплиты
- пока **НЕ** поддерживаются сделки Forex, сделка пропускается и выводится сообщение о том, что это может повлиять на итоговый отчет

*Пример отчета:*
![ibtax report example](./images/ibtax_2016.jpg)


### Запуск
Запустить `ibtax` указав в `--activity-reports-dir` и `--confirmation-reports-dir` директории отчетами в формате `.csv` (см. *Подготовка отчетов Interactive Brokers*)

Важно, чтобы csv-отчеты `activity` и `confirmation` были в разных директориях!

### Подготовка отчетов Interactive Brokers
Для работы нужно выгрузить из [личного кабинета](https://www.interactivebrokers.co.uk/sso/Login) два типа отчетов: *Activity statement* (сделки, дивиденды, информация по инструментам и т.п.) и *Trade Confirmation* (settlement date, необходимая для правильной конвертации сумм по курсу ЦБ)

#### Activity statement
Для загрузки нужно перейти в **Reports / Tax Docs** > **Default Statements** > **Activity**

Выбрать `Format: CSV` и скачать данные за все доступное время (`Perioid: Annual` для прошлых лет + `Period: Year to Date` для текущего года)

**Обязательно выгрузите отчеты за все время существования вашего счета!**

![Activity Statement](./images/ib_report_activity.jpg)

#### Trade Confirmation

Для загрузки нужно перейти в **Reports / Tax Docs** > **Flex Queries** > **Trade Confirmation Flex Query** и создать новый тип отчетов, выбрав в **Sections** > **Trade Confirmation** все пункты в группе **Executions**, остальные настройки - как на скриншоте:

![Trade Confirmation Flex Query](./images/ib_trade_confirmation_settings.jpg)

После этого в **Reports / Tax Docs** > **Custom Statements** выгрузите отчеты **за все время существования вашего счета**, используя `Custom date range` периодами по 1 году (больше IB поставить не дает):


![Trade Confirmation Statement](./images/ib_report_trade_confirmation.jpg)


## Разворачивание проекта для внесения изменений

- Install [poetry](https://python-poetry.org/docs/#installation)
- Clone & modify & run

```
$ git clone https://github.com/cdump/investments

$ cd investments

$ poetry install
$ poetry run ibtax
usage: ibtax [-h] --activity-reports-dir ACTIVITY_REPORTS_DIR --confirmation-reports-dir CONFIRMATION_REPORTS_DIR [--cache-dir CACHE_DIR] [--years YEARS] [--verbose]
ibtax: error: the following arguments are required: --activity-reports-dir, --confirmation-reports-dir

$ vim investments/ibtax/ibtax.py # edit main file for example

$ poetry run ibtax # run updated version
```