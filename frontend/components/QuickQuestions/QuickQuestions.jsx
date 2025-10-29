"use client";

import { useState } from "react";
import styles from "./QuickQuestions.module.css";

const questionsByCategory = {
  "Общие вопросы": [
    "Как правильно провести ретроспективу спринта?",
    "Какой шаблон использовать для отчета руководству?",
    "Как эскалировать проблему с бюджетом проекта?",
    "Как правильно описать задачу разработчику?",
  ],
  "Процессы работы с проектами": [
    "Слушай, как мне правильно провести первую встречу с новым клиентом? Что важно не забыть?",
    "Підкажи, які кроки треба зробити, коли приймаємо проект після пресейлу?",
    "Як заповнити таблицю завантаження команди на місяць? Є якийсь приклад?",
    "Подскажи процесс согласования результатов с клиентом - что и в какой последовательности делать?",
  ],
  "Обязанности и роли": [
    "Можешь рассказать, что входит в мои обязанности как PM?",
    "Яка різниця між Lead PM та звичайним PM? Що додається в обов'язки?",
    "Как пользоваться PM Team Workload? Для чего эта штука вообще?",
    "Які навички повинен мати проджект менеджер у нас в компанії?",
  ],
  "Взаимодействие с клиентами": [
    "Помоги составить подпись для email. Что там должно быть?",
    "Як додати наш Halo PM до Slack клієнта? Є інструкція?",
    "Первый созвон с клиентом скоро. Что обсуждать, как подготовиться?",
    "Как разделить зоны ответственности между нами и клиентом?",
  ],
  "Инструменты и системы": [
    "Как работать с нашим таск-трекером? Есть гайд какой-то?",
    "Як правильно шарити документи в Notion? Щоб всі бачили",
    "Нужно настроить WhatsApp Business. С чего начать?",
    "Расскажи про Tikito - как там работать с контрактами?",
  ],
  "Специфические процессы": [
    "Как контролировать время по проекту? Какие метрики смотреть?",
    "Де збирати відгуки для Clutch? І як часто це робити?",
    "На проекте все пошло не так. Что делать в первую очередь?",
    "Як провести ретроспективу після завершення проекту?",
    "Клиент не хочет наш вариант дизайна. Как убедить?",
    "По проекту закончились задачи. Что делать дальше?",
    "Розкажи про особливості Fixed Price проектів",
    "В чем ценность PM для компании? Как это измерить?",
  ],
"Sales & Account": [
    "Что такое NDA? Когда его подписывать с клиентом?",
    "Як працювати з Production Roadmaps? Для чого вони?",
    "Сейлы передают мне проект. Что я должен получить от них?",
    "Какие типы контрактов мы используем? Когда какой выбирать?",
    "Як сейлз менеджер створює проект в Notion? Можу я це зробити сам?",
    "Кого тегать в канале #production-workload когда нужна помощь?"
  ],
"Брифы и документация": [
    "Нужен шаблон брифа для брендинга. Где найти актуальный?",
    "Допоможи заповнити бриф для сайту. Що там обов'язково має бути?",
    "Какие поля критичны в брифе для веб-проекта?",
    "Клиент хочет мобильное приложение. Какой бриф использовать?",
    "Як правильно оформити бриф для ілюстрацій?",
    "Нужно написать отчет PM Report. Есть пример или шаблон?",
    "Как оценивать дизайн-проекты? Есть методология?",
    "Що таке change request і як його оформити?",
  ]
};

export default function QuickQuestions({ onSelectQuestion, isOpen, onClose }) {
  const [selectedCategory, setSelectedCategory] = useState("Общие вопросы");

  if (!isOpen) return null;

  const categories = Object.keys(questionsByCategory);
  const questions = questionsByCategory[selectedCategory] || [];

  const handleQuestionClick = (question) => {
    onSelectQuestion(question);
  };

  return (
    <div className={styles.overlay} onClick={onClose}>
      <div className={styles.modal} onClick={(e) => e.stopPropagation()}>
        <div className={styles.header}>
          <h3>Быстрые вопросы</h3>
          <button className={styles.closeButton} onClick={onClose}>
            ×
          </button>
        </div>

        <div className={styles.content}>
          <div className={styles.categories}>
            {categories.map((category) => (
              <button
                key={category}
                className={`${styles.categoryButton} ${selectedCategory === category ? styles.active : ""}`}
                onClick={() => setSelectedCategory(category)}
              >
                {category}
              </button>
            ))}
          </div>

          <div className={styles.questions}>
            {questions.map((question, index) => (
              <button key={index} className={styles.questionButton} onClick={() => handleQuestionClick(question)}>
                {question}
              </button>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
