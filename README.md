# Investments
Расчет прибыли Interactive Brokers для уплаты налогов для резидентов РФ

- расчет сделок по методу ФИФО, учет даты рассчетов (settle date)
- конвертация по курсу ЦБ
- раздельный результат сделок по акциям и опционам + дивиденды

*Пример отчета:*
![ibtax report example](./images/ibtax_2016.jpg)

## Установка
```
$ pip install investments --user
```
или с помощью [poetry](https://python-poetry.org/)

## Запуск
Запустить `ibtax` указав в `--activity-reports-dir` и `--confirmation-reports-dir` директории отчетами в формате `.csv` (см. *Подготовка отчетов Interactive Brokers*)

## Подготовка отчетов Interactive Brokers
Для работы нужно выгрузить из [личного кабинета](https://www.interactivebrokers.co.uk/sso/Login) два типа отчетов: *Activity statement* (сделки, дивиденды, информация по инструментам и т.п.) и *Trade Confirmation* (settlement date, необходимая для правильной конвертации сумм по курсу ЦБ)

### Activity statement
Для загрузки нужно перейти в **Reports / Tax Docs** > **Default Statements** > **Activity**

Выбрать `Format: CSV` и скачать данные за все доступное время (`Perioid: Annual` для прошлых лет + `Period: Year to Date` для текущего года)

**Обязательно выгрузите отчеты за все время существования вашего счета!**

![Activity Statement](./images/ib_report_activity.jpg)

### Trade Confirmation

Для загрузки нужно перейти в **Reports / Tax Docs** > **Flex Queries** > **Trade Confirmation Flex Query** и создать новый тип отчетов, выбрав в **Sections** > **Trade Confirmation** все пункты в группе **Executions**, остальные настройки - как на скриншоте:

![Trade Confirmation Flex Query](./images/ib_trade_confirmation_settings.jpg)

После этого в **Reports / Tax Docs** > **Custom Statements** выгрузите отчеты **за все время существования вашего счета**, используя `Custom date range` периодами по 1 году (больше IB поставить не дает):


![Trade Confirmation Statement](./images/ib_report_trade_confirmation.jpg)
