    OGG VORBIS

������: 2
  
�����: ����� ������
    
    ��������
        
������ ���������� ����� ��������� ���������� �� ogg vorbis ����� ����� � 
    ������������� ���    

    ����������
    
-- Python 3.5

    ������
    
-- tests -> ����� � �������. ������:
    -- pathmagic.py -> ������� ����-������� ��� ������ E402 PEP'a
    -- test_clients.py -> ����� �������� (���� ��� ������ �����������)
    -- test_codebook_decoder.py -> ����� �������� �������������� ������
    -- test_ogg.py -> ����� �������� ���������� ogg
    -- test_vorbis_main.py -> ����� �������� �������� ����� ������ vorbis
-- vorbis -> ����� ������ ��� ������ � ���������� ogg vorbis ������. 
    ����������:
    -- codebook.py -> ������� �������������� ������
    -- errors.py -> �������� ���������� ����� ������ ����� ������
    -- helper_funcs.py -> �������� ��������������� ������� ��������� ����������
    -- ogg.py -> ������� ���������� ogg. ���������� vorbis-������ �� 
        ogg-�������
    -- vorbis_main.py -> ������� ������� ���� ������ vorbis. ��������������� 
        ������������ vorbis-������
-- ogg_vorbis_cs.py -> ���������� ������ ����������

    ���������� ������
    
������� �� �������: ogg_vorbis_cs.py --help

������ �������: ogg_vorbis_cs.py --headers=ident Immortal.ogg

������� �� ��������: --help [�������� �������]

    ����������� ����������
    
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

    