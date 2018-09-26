    OGG VORBIS

Версия: 2
  
Автор: Семен Вяцков
    
    ОПИСАНИЕ
        
Данное приложение пишет подробную информацию об ogg vorbis аудио файле и 
    воспроизводит его    

    ТРЕБОВАНИЯ
    
-- Python 3.5

    СОСТАВ
    
-- tests -> Папка с тестами. Состав:
    -- pathmagic.py -> Кодовый файл-костыль для обхода E402 PEP'a
    -- test_clients.py -> Тесты клиентов (пока что только консольного)
    -- test_codebook_decoder.py -> Тесты декодера дешифровальных таблиц
    -- test_ogg.py -> Тесты декодера контейнера ogg
    -- test_vorbis_main.py -> Тесты главного кодового файла модуля vorbis
-- vorbis -> Папка модуля для работы с содержимым ogg vorbis файлов. 
    Содержимое:
    -- codebook.py -> Декодер дешифровальных таблиц
    -- errors.py -> Содержит переменные кодов ошибок всего модуля
    -- helper_funcs.py -> Содержит вспомогательные функции различных назначений
    -- ogg.py -> Декодер контейнера ogg. Декодирует vorbis-пакеты из 
        ogg-страниц
    -- vorbis_main.py -> Главный кодовый файл модуля vorbis. Непосредственно 
        обрабатывает vorbis-пакеты
-- ogg_vorbis_cs.py -> Консольный клиент приложения

    КОНСОЛЬНАЯ ВЕРСИЯ
    
Справка по запуску: ogg_vorbis_cs.py --help

Пример запуска: ogg_vorbis_cs.py --headers=ident Immortal.ogg

Справка по командам: --help [аргумент запуска]

    ПОДРОБНОСТИ РЕАЛИЗАЦИИ
    
Name                             Stmts   Miss  Cover
----------------------------------------------------
ogg_vorbis_cs.py                    48      9    81%
tests\pathmagic.py                   3      0   100%
tests\test_clients.py               30      0   100%
tests\test_codebook_decoder.py      65      1    98%
tests\test_ogg.py                   49      2    96%
tests\test_vorbis_main.py           89      1    99%
vorbis\__init__.py                   0      0   100%
vorbis\codebook.py                 125     22    82%
vorbis\errors.py                    19      0   100%
vorbis\helper_funcs.py              26      1    96%
vorbis\ogg.py                       68      9    87%
vorbis\vorbis_main.py              165     27    84%
----------------------------------------------------
TOTAL                              700     85    88%

    