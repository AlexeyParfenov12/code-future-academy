"""Reproducible, explicitly authored example; never substitutes absent archive files."""
from pathlib import Path
import ast,csv,hashlib,io,json,zipfile

ROOT=Path(__file__).resolve().parents[1]
def load(name):return json.loads((ROOT/'content/solutions'/name).read_text(encoding='utf8'))
def sha(data):return hashlib.sha256(data).hexdigest()
def build():
    documentation=load('m04-documentation.json')['solutions']
    code=next(s['code'] for s in documentation if s['code'])
    samples=next(s['code'] for s in load('m04-v2.json')['solutions'] if 'TEXTS_BY_CATEGORY' in s['code'])
    tree=ast.parse(samples)
    data=next(ast.literal_eval(n.value) for n in tree.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='TEXTS_BY_CATEGORY' for t in n.targets))
    csvout=io.StringIO(newline='');writer=csv.writer(csvout,lineterminator='\n')
    writer.writerow(['text','expected_category'])
    labels={'сеть':'network','доступ':'access','оборудование':'equipment','по':'software'}
    for category,texts in data.items():
        for text in texts:writer.writerow([text,labels[category]])
    dataset=csvout.getvalue().encode('utf8')
    files={
        'src/main_v2_0.py':code.encode('utf8'),
        'data/tickets_v1_3.csv':dataset,
        'docs/README.md':(
            '# Campus Support / самостоятельный пример\n\n'
            'Учебный комплект Code Future Academy, подготовлен 02.11.2026.\n'
            'Это авторский пример структуры задания 4.13. Отсутствующие main_final2.py, tickets_new.csv и old_model.py не выдаются за восстановленные оригиналы.\n\n'
            'Запуск из корня комплекта: python src/main_v2_0.py. Нужен Python 3.11+, внешних библиотек нет.\n'
            'Программа показывает шесть сценариев из практики 4.13 и проверяет ожидаемые результаты assert. Порог ручной проверки 0.60, confidence передаётся сценарием, не рассчитывается моделью.\n'
            'Это маршрутизатор по правилам, а не обученная ML-модель 4.10. Данные здесь не используются для обучения.\n\n'
            'CSV: 64 синтетических текста, четыре категории по 16. Тексты взяты из опубликованного проверенного примера 4.10, названия классов переведены в английские идентификаторы.\n'
            'Версия data 1.3 обозначает версию этого самостоятельного комплекта. Размер, распределение и хеш не приписываются неизвестному tickets_new.csv из условия.\n'
            'Персональных данных реальных пользователей нет. Для применения нужны отдельная проверка качества, политика доступа и согласование обработки данных.\n'
        ).encode('utf8'),
        'docs/data-passport.json':json.dumps({'origin':'Синтетические тексты проверенного решения обычной практики 4.10','rows':sum(map(len,data.values())),'classes':{labels[k]:len(v) for k,v in data.items()},'bytes':len(dataset),'sha256':sha(dataset),'productVersion':'2.0','dataVersion':'1.3','createdAt':'2026-11-02'},ensure_ascii=False,indent=2).encode('utf8'),
        'reports/expected-results.txt':next(s['tests'][0]['expected'] for s in documentation if s['code']).encode('utf8'),
        'archive/README.txt':'Предыдущая версия исходной модели в комплекте задания отсутствует. Фиктивный old_model.py не создан.\n'.encode('utf8')
    }
    files['manifest.json']=json.dumps({'createdAt':'2026-11-02','authoredExample':True,'files':{name:sha(data) for name,data in files.items()}},ensure_ascii=False,indent=2).encode('utf8')
    output=ROOT/'public/content/examples/campus-support-4-13.zip';output.parent.mkdir(parents=True,exist_ok=True)
    with zipfile.ZipFile(output,'w',compression=zipfile.ZIP_DEFLATED) as archive:
        for name,payload in sorted(files.items()):
            info=zipfile.ZipInfo(name,date_time=(2026,11,2,0,0,0));info.compress_type=zipfile.ZIP_DEFLATED
            archive.writestr(info,payload)
    print(json.dumps({'artifact':output.name,'files':len(files),'rows':sum(map(len,data.values()))}))
if __name__=='__main__':build()
