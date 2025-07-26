#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
词典管理器 - Dictionary Manager
负责加载、管理和提供各种词库数据
"""

import json
import os
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass

@dataclass
class Word:
    """单词数据类"""
    word: str
    translation: str
    phonetic: str = ""
    difficulty: int = 1
    category: str = ""
    example: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "word": self.word,
            "translation": self.translation,
            "phonetic": self.phonetic,
            "difficulty": self.difficulty,
            "category": self.category,
            "example": self.example
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Word':
        """从字典创建"""
        return cls(
            word=data.get("word", ""),
            translation=data.get("translation", ""),
            phonetic=data.get("phonetic", ""),
            difficulty=data.get("difficulty", 1),
            category=data.get("category", ""),
            example=data.get("example", "")
        )

@dataclass
class Dictionary:
    """词典数据类"""
    name: str
    description: str
    words: List[Word]
    total_words: int = 0
    chapters: int = 0
    words_per_chapter: int = 20
    
    def __post_init__(self):
        self.total_words = len(self.words)
        self.chapters = (self.total_words + self.words_per_chapter - 1) // self.words_per_chapter
    
    def get_chapter_words(self, chapter: int) -> List[Word]:
        """获取指定章节的单词"""
        start_idx = chapter * self.words_per_chapter
        end_idx = min(start_idx + self.words_per_chapter, self.total_words)
        return self.words[start_idx:end_idx]
    
    def get_word_by_index(self, index: int) -> Optional[Word]:
        """根据索引获取单词"""
        if 0 <= index < self.total_words:
            return self.words[index]
        return None

class DictionaryManager:
    """词典管理器"""
    
    def __init__(self):
        self.dictionaries: Dict[str, Dictionary] = {}
        self.current_dictionary: Optional[Dictionary] = None
        self.data_dir = Path(__file__).parent.parent.parent / "data" / "dictionaries"
        self._load_built_in_dictionaries()
    
    def _load_built_in_dictionaries(self):
        """加载内置词典"""
        # 创建内置词典数据
        built_in_dicts = {
            "cet4": self._create_cet4_dict(),
            "cet6": self._create_cet6_dict(),
            "gre": self._create_gre_dict(),
            "toefl": self._create_toefl_dict(),
            "ielts": self._create_ielts_dict(),
            "gmat": self._create_gmat_dict(),
            "sat": self._create_sat_dict(),
            "coder": self._create_coder_dict()
        }
        
        for dict_id, dictionary in built_in_dicts.items():
            self.dictionaries[dict_id] = dictionary
        
        # 尝试从文件加载自定义词典
        self._load_custom_dictionaries()
    
    def _create_cet4_dict(self) -> Dictionary:
        """创建CET-4词典"""
        words_data = [
            {"word": "abandon", "translation": "放弃，抛弃", "phonetic": "/əˈbændən/", "difficulty": 2},
            {"word": "ability", "translation": "能力，才能", "phonetic": "/əˈbɪləti/", "difficulty": 1},
            {"word": "able", "translation": "能够的，有能力的", "phonetic": "/ˈeɪbl/", "difficulty": 1},
            {"word": "about", "translation": "关于，大约", "phonetic": "/əˈbaʊt/", "difficulty": 1},
            {"word": "above", "translation": "在...上面", "phonetic": "/əˈbʌv/", "difficulty": 1},
            {"word": "abroad", "translation": "在国外", "phonetic": "/əˈbrɔːd/", "difficulty": 2},
            {"word": "absence", "translation": "缺席，不在", "phonetic": "/ˈæbsəns/", "difficulty": 2},
            {"word": "absent", "translation": "缺席的，不在的", "phonetic": "/ˈæbsənt/", "difficulty": 2},
            {"word": "absolute", "translation": "绝对的，完全的", "phonetic": "/ˈæbsəluːt/", "difficulty": 3},
            {"word": "absorb", "translation": "吸收，吸取", "phonetic": "/əbˈsɔːb/", "difficulty": 2},
            {"word": "abstract", "translation": "抽象的", "phonetic": "/ˈæbstrækt/", "difficulty": 3},
            {"word": "academic", "translation": "学术的，学院的", "phonetic": "/ˌækəˈdemɪk/", "difficulty": 2},
            {"word": "accept", "translation": "接受，承认", "phonetic": "/əkˈsept/", "difficulty": 1},
            {"word": "access", "translation": "接近，进入", "phonetic": "/ˈækses/", "difficulty": 2},
            {"word": "accident", "translation": "事故，意外", "phonetic": "/ˈæksɪdənt/", "difficulty": 2},
            {"word": "accompany", "translation": "陪伴，伴随", "phonetic": "/əˈkʌmpəni/", "difficulty": 2},
            {"word": "accomplish", "translation": "完成，实现", "phonetic": "/əˈkʌmplɪʃ/", "difficulty": 3},
            {"word": "according", "translation": "根据，按照", "phonetic": "/əˈkɔːdɪŋ/", "difficulty": 2},
            {"word": "account", "translation": "账户，解释", "phonetic": "/əˈkaʊnt/", "difficulty": 2},
            {"word": "accurate", "translation": "准确的，精确的", "phonetic": "/ˈækjərət/", "difficulty": 2}
        ]
        
        words = [Word.from_dict(word_data) for word_data in words_data]
        return Dictionary(
            name="CET-4 词汇",
            description="大学英语四级考试词汇",
            words=words
        )
    
    def _create_cet6_dict(self) -> Dictionary:
        """创建CET-6词典"""
        words_data = [
            {"word": "abbreviation", "translation": "缩写，缩略", "phonetic": "/əˌbriːviˈeɪʃn/", "difficulty": 3},
            {"word": "abide", "translation": "遵守，忍受", "phonetic": "/əˈbaɪd/", "difficulty": 3},
            {"word": "abolish", "translation": "废除，取消", "phonetic": "/əˈbɒlɪʃ/", "difficulty": 3},
            {"word": "abortion", "translation": "流产，堕胎", "phonetic": "/əˈbɔːʃn/", "difficulty": 3},
            {"word": "abrupt", "translation": "突然的，唐突的", "phonetic": "/əˈbrʌpt/", "difficulty": 3},
            {"word": "absurd", "translation": "荒谬的，可笑的", "phonetic": "/əbˈsɜːd/", "difficulty": 3},
            {"word": "abundance", "translation": "丰富，充裕", "phonetic": "/əˈbʌndəns/", "difficulty": 3},
            {"word": "academy", "translation": "学院，研究院", "phonetic": "/əˈkædəmi/", "difficulty": 2},
            {"word": "accelerate", "translation": "加速，促进", "phonetic": "/əkˈseləreɪt/", "difficulty": 3},
            {"word": "accessory", "translation": "附件，配件", "phonetic": "/əkˈsesəri/", "difficulty": 3}
        ]
        
        words = [Word.from_dict(word_data) for word_data in words_data]
        return Dictionary(
            name="CET-6 词汇",
            description="大学英语六级考试词汇",
            words=words
        )
    
    def _create_gre_dict(self) -> Dictionary:
        """创建GRE词典"""
        words_data = [
            {"word": "abate", "translation": "减少，减轻", "phonetic": "/əˈbeɪt/", "difficulty": 4},
            {"word": "aberrant", "translation": "异常的，偏离的", "phonetic": "/æˈberənt/", "difficulty": 4},
            {"word": "abeyance", "translation": "暂停，中止", "phonetic": "/əˈbeɪəns/", "difficulty": 4},
            {"word": "abscond", "translation": "潜逃，逃匿", "phonetic": "/əbˈskɒnd/", "difficulty": 4},
            {"word": "abstain", "translation": "戒除，避免", "phonetic": "/əbˈsteɪn/", "difficulty": 4},
            {"word": "admonish", "translation": "告诫，劝告", "phonetic": "/ədˈmɒnɪʃ/", "difficulty": 4},
            {"word": "adulterate", "translation": "掺假，使不纯", "phonetic": "/əˈdʌltəreɪt/", "difficulty": 4},
            {"word": "aesthetic", "translation": "美学的，审美的", "phonetic": "/iːsˈθetɪk/", "difficulty": 4},
            {"word": "affable", "translation": "和蔼的，友善的", "phonetic": "/ˈæfəbl/", "difficulty": 4},
            {"word": "aggrandize", "translation": "扩大，增强", "phonetic": "/əˈɡrændaɪz/", "difficulty": 4}
        ]
        
        words = [Word.from_dict(word_data) for word_data in words_data]
        return Dictionary(
            name="GRE 词汇",
            description="研究生入学考试词汇",
            words=words
        )
    
    def _create_toefl_dict(self) -> Dictionary:
        """创建TOEFL词典"""
        words_data = [
            {"word": "accommodate", "translation": "容纳，适应", "phonetic": "/əˈkɒmədeɪt/", "difficulty": 3},
            {"word": "accumulate", "translation": "积累，堆积", "phonetic": "/əˈkjuːmjəleɪt/", "difficulty": 3},
            {"word": "acknowledge", "translation": "承认，确认", "phonetic": "/əkˈnɒlɪdʒ/", "difficulty": 3},
            {"word": "acquire", "translation": "获得，取得", "phonetic": "/əˈkwaɪə/", "difficulty": 3},
            {"word": "adequate", "translation": "足够的，适当的", "phonetic": "/ˈædɪkwət/", "difficulty": 3},
            {"word": "adjacent", "translation": "邻近的，毗邻的", "phonetic": "/əˈdʒeɪsnt/", "difficulty": 3},
            {"word": "advocate", "translation": "提倡，拥护", "phonetic": "/ˈædvəkeɪt/", "difficulty": 3},
            {"word": "aggregate", "translation": "总计，聚集", "phonetic": "/ˈæɡrɪɡət/", "difficulty": 3},
            {"word": "allocate", "translation": "分配，分派", "phonetic": "/ˈæləkeɪt/", "difficulty": 3},
            {"word": "alternative", "translation": "替代的，可选择的", "phonetic": "/ɔːlˈtɜːnətɪv/", "difficulty": 3}
        ]
        
        words = [Word.from_dict(word_data) for word_data in words_data]
        return Dictionary(
            name="TOEFL 词汇",
            description="托福考试词汇",
            words=words
        )
    
    def _create_ielts_dict(self) -> Dictionary:
        """创建IELTS词典"""
        words_data = [
            {"word": "analyze", "translation": "分析，解析", "phonetic": "/ˈænəlaɪz/", "difficulty": 3},
            {"word": "approach", "translation": "方法，接近", "phonetic": "/əˈprəʊtʃ/", "difficulty": 2},
            {"word": "appropriate", "translation": "适当的，合适的", "phonetic": "/əˈprəʊpriət/", "difficulty": 3},
            {"word": "approximate", "translation": "大约的，近似的", "phonetic": "/əˈprɒksɪmət/", "difficulty": 3},
            {"word": "aspect", "translation": "方面，外观", "phonetic": "/ˈæspekt/", "difficulty": 2},
            {"word": "assess", "translation": "评估，评价", "phonetic": "/əˈses/", "difficulty": 3},
            {"word": "assume", "translation": "假设，承担", "phonetic": "/əˈsjuːm/", "difficulty": 2},
            {"word": "attitude", "translation": "态度，看法", "phonetic": "/ˈætɪtjuːd/", "difficulty": 2},
            {"word": "attribute", "translation": "属性，归因于", "phonetic": "/əˈtrɪbjuːt/", "difficulty": 3},
            {"word": "authority", "translation": "权威，当局", "phonetic": "/ɔːˈθɒrəti/", "difficulty": 2}
        ]
        
        words = [Word.from_dict(word_data) for word_data in words_data]
        return Dictionary(
            name="IELTS 词汇",
            description="雅思考试词汇",
            words=words
        )
    
    def _create_gmat_dict(self) -> Dictionary:
        """创建GMAT词典"""
        words_data = [
            {"word": "ambiguous", "translation": "模糊的，含糊的", "phonetic": "/æmˈbɪɡjuəs/", "difficulty": 4},
            {"word": "analogous", "translation": "类似的，相似的", "phonetic": "/əˈnæləɡəs/", "difficulty": 4},
            {"word": "arbitrary", "translation": "任意的，专断的", "phonetic": "/ˈɑːbɪtrəri/", "difficulty": 4},
            {"word": "coherent", "translation": "连贯的，一致的", "phonetic": "/kəʊˈhɪərənt/", "difficulty": 4},
            {"word": "comprehensive", "translation": "全面的，综合的", "phonetic": "/ˌkɒmprɪˈhensɪv/", "difficulty": 3},
            {"word": "constitute", "translation": "构成，组成", "phonetic": "/ˈkɒnstɪtjuːt/", "difficulty": 3},
            {"word": "contemporary", "translation": "当代的，现代的", "phonetic": "/kənˈtemprəri/", "difficulty": 3},
            {"word": "controversy", "translation": "争议，争论", "phonetic": "/ˈkɒntrəvɜːsi/", "difficulty": 3},
            {"word": "criteria", "translation": "标准，准则", "phonetic": "/kraɪˈtɪəriə/", "difficulty": 3},
            {"word": "demonstrate", "translation": "证明，演示", "phonetic": "/ˈdemənstreɪt/", "difficulty": 3}
        ]
        
        words = [Word.from_dict(word_data) for word_data in words_data]
        return Dictionary(
            name="GMAT 词汇",
            description="管理学研究生入学考试词汇",
            words=words
        )
    
    def _create_sat_dict(self) -> Dictionary:
        """创建SAT词典"""
        words_data = [
            {"word": "abundant", "translation": "丰富的，充足的", "phonetic": "/əˈbʌndənt/", "difficulty": 3},
            {"word": "acclaim", "translation": "赞扬，喝彩", "phonetic": "/əˈkleɪm/", "difficulty": 3},
            {"word": "adversary", "translation": "对手，敌手", "phonetic": "/ˈædvəsəri/", "difficulty": 3},
            {"word": "advocate", "translation": "支持者，拥护者", "phonetic": "/ˈædvəkət/", "difficulty": 3},
            {"word": "aesthetic", "translation": "美的，审美的", "phonetic": "/iːsˈθetɪk/", "difficulty": 4},
            {"word": "alleviate", "translation": "减轻，缓解", "phonetic": "/əˈliːvieɪt/", "difficulty": 4},
            {"word": "ambivalent", "translation": "矛盾的，摇摆的", "phonetic": "/æmˈbɪvələnt/", "difficulty": 4},
            {"word": "amiable", "translation": "和蔼的，友善的", "phonetic": "/ˈeɪmiəbl/", "difficulty": 3},
            {"word": "ample", "translation": "充足的，宽敞的", "phonetic": "/ˈæmpl/", "difficulty": 3},
            {"word": "animosity", "translation": "敌意，仇恨", "phonetic": "/ˌænɪˈmɒsəti/", "difficulty": 4}
        ]
        
        words = [Word.from_dict(word_data) for word_data in words_data]
        return Dictionary(
            name="SAT 词汇",
            description="学术能力评估测试词汇",
            words=words
        )
    
    def _create_coder_dict(self) -> Dictionary:
        """创建程序员词典"""
        words_data = [
            {"word": "algorithm", "translation": "算法", "phonetic": "/ˈælɡərɪðəm/", "difficulty": 2},
            {"word": "array", "translation": "数组", "phonetic": "/əˈreɪ/", "difficulty": 1},
            {"word": "boolean", "translation": "布尔值", "phonetic": "/ˈbuːliən/", "difficulty": 2},
            {"word": "class", "translation": "类", "phonetic": "/klɑːs/", "difficulty": 1},
            {"word": "compile", "translation": "编译", "phonetic": "/kəmˈpaɪl/", "difficulty": 2},
            {"word": "debug", "translation": "调试", "phonetic": "/diːˈbʌɡ/", "difficulty": 2},
            {"word": "exception", "translation": "异常", "phonetic": "/ɪkˈsepʃn/", "difficulty": 2},
            {"word": "function", "translation": "函数", "phonetic": "/ˈfʌŋkʃn/", "difficulty": 1},
            {"word": "interface", "translation": "接口", "phonetic": "/ˈɪntəfeɪs/", "difficulty": 2},
            {"word": "iteration", "translation": "迭代", "phonetic": "/ˌɪtəˈreɪʃn/", "difficulty": 3},
            {"word": "library", "translation": "库", "phonetic": "/ˈlaɪbrəri/", "difficulty": 1},
            {"word": "method", "translation": "方法", "phonetic": "/ˈmeθəd/", "difficulty": 1},
            {"word": "object", "translation": "对象", "phonetic": "/ˈɒbdʒɪkt/", "difficulty": 1},
            {"word": "parameter", "translation": "参数", "phonetic": "/pəˈræmɪtə/", "difficulty": 2},
            {"word": "query", "translation": "查询", "phonetic": "/ˈkwɪəri/", "difficulty": 2},
            {"word": "recursion", "translation": "递归", "phonetic": "/rɪˈkɜːʃn/", "difficulty": 3},
            {"word": "syntax", "translation": "语法", "phonetic": "/ˈsɪntæks/", "difficulty": 2},
            {"word": "thread", "translation": "线程", "phonetic": "/θred/", "difficulty": 2},
            {"word": "variable", "translation": "变量", "phonetic": "/ˈveəriəbl/", "difficulty": 1},
            {"word": "framework", "translation": "框架", "phonetic": "/ˈfreɪmwɜːk/", "difficulty": 2}
        ]
        
        words = [Word.from_dict(word_data) for word_data in words_data]
        return Dictionary(
            name="程序员词汇",
            description="程序员常用英语词汇",
            words=words
        )
    
    def _load_custom_dictionaries(self):
        """加载自定义词典"""
        if not self.data_dir.exists():
            return
        
        for dict_file in self.data_dir.glob("*.json"):
            try:
                with open(dict_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                words = [Word.from_dict(word_data) for word_data in data.get("words", [])]
                dictionary = Dictionary(
                    name=data.get("name", dict_file.stem),
                    description=data.get("description", ""),
                    words=words
                )
                
                dict_id = dict_file.stem
                self.dictionaries[dict_id] = dictionary
                
            except Exception as e:
                print(f"加载词典文件 {dict_file} 失败: {e}")
    
    def get_dictionary_list(self) -> List[Dict[str, str]]:
        """获取词典列表"""
        return [
            {
                "id": dict_id,
                "name": dictionary.name,
                "description": dictionary.description,
                "total_words": dictionary.total_words,
                "chapters": dictionary.chapters
            }
            for dict_id, dictionary in self.dictionaries.items()
        ]
    
    def load_dictionary(self, dict_id: str) -> bool:
        """加载指定词典"""
        if dict_id in self.dictionaries:
            self.current_dictionary = self.dictionaries[dict_id]
            return True
        return False
    
    def get_current_dictionary(self) -> Optional[Dictionary]:
        """获取当前词典"""
        return self.current_dictionary
    
    def save_custom_dictionary(self, dict_id: str, dictionary: Dictionary) -> bool:
        """保存自定义词典"""
        try:
            # 确保目录存在
            self.data_dir.mkdir(parents=True, exist_ok=True)
            
            # 准备数据
            data = {
                "name": dictionary.name,
                "description": dictionary.description,
                "words": [word.to_dict() for word in dictionary.words]
            }
            
            # 保存到文件
            dict_file = self.data_dir / f"{dict_id}.json"
            with open(dict_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            
            # 添加到内存中的词典列表
            self.dictionaries[dict_id] = dictionary
            
            return True
        except Exception as e:
            print(f"保存词典失败: {e}")
            return False