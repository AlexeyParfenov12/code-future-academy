# Учебный проект: синтетические сообщения, не производственный фильтр.
TRAIN = [('срочно сообщите код подтверждения', 'risk'),
 ('пришлите пароль от учётной записи', 'risk'),
 ('переведите деньги для получения выигрыша', 'risk'),
 ('вы выиграли приз отправьте деньги', 'risk'),
 ('сообщите номер карты и код безопасности', 'risk'),
 ('введите пароль по ссылке', 'risk'),
 ('подтвердите карту по неизвестной ссылке', 'risk'),
 ('срочно оплатите комиссию за приз', 'risk'),
 ('пришлите код из сообщения', 'risk'),
 ('ваш аккаунт заблокирован сообщите пароль', 'risk'),
 ('срочно переведите деньги на новый счет', 'risk'),
 ('назовите код доступа оператору', 'risk'),
 ('вы выиграли деньги подтвердите карту', 'risk'),
 ('отправьте пароль для разблокировки', 'risk'),
 ('введите данные карты для получения приза', 'risk'),
 ('оплатите выигрыш переводом', 'risk'),
 ('передайте одноразовый код', 'risk'),
 ('подтвердите логин и пароль', 'risk'),
 ('переведите оплату для получения подарка', 'risk'),
 ('сообщите секретный код', 'risk'),
 ('встреча команды завтра в десять', 'ordinary'),
 ('пожалуйста проверьте расписание занятий', 'ordinary'),
 ('лекция начнется после обеда', 'ordinary'),
 ('отчет по проекту готов', 'ordinary'),
 ('книга доступна в библиотеке', 'ordinary'),
 ('приходите на консультацию по проекту', 'ordinary'),
 ('завтра обсуждаем план работы', 'ordinary'),
 ('проверьте свои результаты в кабинете', 'ordinary'),
 ('занятие перенесено на пятницу', 'ordinary'),
 ('презентация доступна на учебном сайте', 'ordinary'),
 ('напоминаю о собрании группы', 'ordinary'),
 ('спасибо за участие во встрече', 'ordinary'),
 ('готовлю отчет по учебной практике', 'ordinary'),
 ('расписание обновлено на сайте', 'ordinary'),
 ('в библиотеке появились новые книги', 'ordinary'),
 ('команда завершила этап проекта', 'ordinary'),
 ('вопросы обсудим на консультации', 'ordinary'),
 ('план занятий отправлен группе', 'ordinary'),
 ('ждем вас на семинаре', 'ordinary'),
 ('материалы лекции опубликованы', 'ordinary')]
TEST = [('срочно пришлите пароль', 'risk'),
 ('для выигрыша переведите деньги', 'risk'),
 ('назовите секретный код', 'risk'),
 ('введите карту по ссылке', 'risk'),
 ('передайте одноразовый пароль', 'risk'),
 ('завтра встреча группы', 'ordinary'),
 ('материалы проекта готовы', 'ordinary'),
 ('книга в библиотеке', 'ordinary'),
 ('расписание занятий на сайте', 'ordinary'),
 ('пришлите отчет по проекту', 'ordinary')]
import argparse
import json
import math
import re
from collections import Counter

def tokens(text):
    if not isinstance(text, str) or not text.strip():
        raise ValueError("Нужен непустой текст")
    result = re.findall(r"[а-яёa-z]+", text.lower())
    if not result:
        raise ValueError("В тексте нет слов")
    return result

class NaiveBayes:
    def fit(self, rows):
        self.classes = sorted({label for _, label in rows})
        self.counts = {label: Counter() for label in self.classes}
        self.documents = Counter(label for _, label in rows)
        for text, label in rows:
            self.counts[label].update(tokens(text))
        self.vocabulary = set().union(*(set(c) for c in self.counts.values()))
        self.total = {label: sum(c.values()) for label,c in self.counts.items()}
        self.rows = len(rows)
        return self

    def predict(self, text):
        words = tokens(text)
        log_scores = {}
        for label in self.classes:
            score = math.log(self.documents[label] / self.rows)
            for word in words:
                if word in self.vocabulary:
                    score += math.log((self.counts[label][word]+1) /
                                      (self.total[label]+len(self.vocabulary)))
            log_scores[label] = score
        maximum = max(log_scores.values())
        weights = {label: math.exp(score-maximum) for label,score in log_scores.items()}
        label = max(weights, key=weights.get)
        score = weights[label] / sum(weights.values())
        return {"label": label, "score": round(score,4),
                "action": "review" if label == "risk" or score < .80 else "ordinary"}

def evaluate(model):
    predicted = [model.predict(text)["label"] for text,_ in TEST]
    actual = [label for _,label in TEST]
    tp = sum(a == "risk" and p == "risk" for a,p in zip(actual,predicted))
    fp = sum(a == "ordinary" and p == "risk" for a,p in zip(actual,predicted))
    fn = sum(a == "risk" and p == "ordinary" for a,p in zip(actual,predicted))
    tn = sum(a == "ordinary" and p == "ordinary" for a,p in zip(actual,predicted))
    return {"trainRows":len(TRAIN),"testRows":len(TEST),"accuracy":(tp+tn)/len(TEST),
            "baselineAccuracy":sum(a == "ordinary" for a in actual)/len(TEST),
            "tp":tp,"fp":fp,"fn":fn,"tn":tn}

def self_test(model):
    assert model.predict("сообщите пароль")["action"] == "review"
    assert model.predict("абракадабра")["action"] == "review"
    for bad in ["", "   ", None, 123, "!!!"]:
        try:
            model.predict(bad)
        except ValueError:
            pass
        else:
            raise AssertionError("Не отклонён некорректный вход")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--text")
    args = parser.parse_args()
    model = NaiveBayes().fit(TRAIN)
    self_test(model)
    if args.text is None:
        print(json.dumps(evaluate(model),ensure_ascii=False,sort_keys=True))
    else:
        try:
            print(json.dumps(model.predict(args.text),ensure_ascii=False))
        except ValueError as error:
            parser.error(str(error))
