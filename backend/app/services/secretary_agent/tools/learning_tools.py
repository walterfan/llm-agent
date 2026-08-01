"""
Learning tools for the Personal Secretary agent.

Provides tools for:
- Learning English words (with Chinese explanations)
- Learning English sentences (with grammar analysis)
- Learning tech topics (structured learning plans)
- Answering questions
- Planning ideas into actionable steps
"""

from typing import Optional

from pydantic import BaseModel, Field


# ============================================================================
# Response Schemas
# ============================================================================


class WordExample(BaseModel):
    """An example sentence for a word."""

    english: str = Field(description="Example sentence in English")
    chinese: str = Field(description="Chinese translation of the example")


class WordResponse(BaseModel):
    """Response schema for learning an English word."""

    word: str = Field(description="The English word")
    pronunciation: str = Field(description="IPA pronunciation, e.g., /səˈrendɪpɪti/")
    part_of_speech: str = Field(
        description="Part of speech: noun, verb, adjective, etc."
    )
    chinese_explanation: str = Field(description="中文解释")
    examples: list[WordExample] = Field(
        description="Usage examples with Chinese translations", min_length=2
    )
    synonyms: list[str] = Field(description="Similar words", default_factory=list)
    collocations: list[str] = Field(
        description="Common word combinations", default_factory=list
    )
    usage_notes: Optional[str] = Field(
        default=None, description="Special usage rules or contexts"
    )


class GrammarPoint(BaseModel):
    """A grammar point in a sentence."""

    pattern: str = Field(description="Grammar pattern name")
    explanation: str = Field(description="Explanation of the pattern")
    example: str = Field(description="Example of this pattern")


class VocabularyItem(BaseModel):
    """A vocabulary item from a sentence."""

    word: str = Field(description="The word or phrase")
    meaning: str = Field(description="Chinese meaning")
    part_of_speech: str = Field(description="Part of speech")


class SentenceResponse(BaseModel):
    """Response schema for learning an English sentence."""

    sentence: str = Field(description="The original English sentence")
    chinese_translation: str = Field(description="中文翻译")
    vocabulary: list[VocabularyItem] = Field(description="Key vocabulary with meanings")
    grammar_points: list[GrammarPoint] = Field(
        description="Grammar patterns used in the sentence"
    )
    similar_sentences: list[dict[str, str]] = Field(
        description="Similar sentences with translations", default_factory=list
    )
    usage_notes: Optional[str] = Field(
        default=None, description="When and how to use this expression"
    )
    common_mistakes: list[str] = Field(
        description="Common mistakes to avoid", default_factory=list
    )


class KeyConcept(BaseModel):
    """A key concept in a tech topic."""

    name: str = Field(description="Concept name")
    name_chinese: str = Field(description="Chinese name")
    description: str = Field(description="Brief explanation")
    importance: str = Field(description="Why it matters")


class LearningStep(BaseModel):
    """A step in the learning path."""

    step: int = Field(description="Step number")
    title: str = Field(description="Step title")
    title_chinese: str = Field(description="Chinese title")
    description: str = Field(description="What to learn")
    duration: str = Field(description="Estimated duration, e.g., '1-2 days'")
    outcomes: list[str] = Field(description="What you'll be able to do")


class Resource(BaseModel):
    """A learning resource."""

    title: str = Field(description="Resource title")
    type: str = Field(description="Type: tutorial, documentation, course, video, book")
    url: Optional[str] = Field(default=None, description="URL if available")
    description: str = Field(description="Brief description")
    difficulty: str = Field(description="beginner, intermediate, advanced")


class TopicResponse(BaseModel):
    """Response schema for learning a tech topic."""

    topic: str = Field(description="The tech topic")
    introduction: str = Field(description="Brief introduction in English")
    introduction_chinese: str = Field(description="中文简介")
    key_concepts: list[KeyConcept] = Field(
        description="Fundamental concepts to understand", min_length=3
    )
    learning_path: list[LearningStep] = Field(
        description="Step-by-step learning progression", min_length=3
    )
    resources: list[Resource] = Field(
        description="Recommended learning resources", min_length=3
    )
    prerequisites: list[str] = Field(
        description="What should the learner know first", default_factory=list
    )
    time_estimate: str = Field(description="Total time estimate, e.g., '2-3 weeks'")
    difficulty: str = Field(description="beginner, intermediate, or advanced")


class ArticleResponse(BaseModel):
    """Response schema for learning from a URL article."""

    url: str = Field(description="Original URL")
    title: str = Field(description="Article title")
    author: Optional[str] = Field(default=None, description="Author if available")
    published_date: Optional[str] = Field(
        default=None, description="Publication date if available"
    )

    # Content
    original_markdown: str = Field(description="Clean markdown of original article")
    bilingual_content: str = Field(
        description="Markdown with English + Chinese translation"
    )

    # Summary
    summary: str = Field(description="Brief summary in Chinese (3-5 sentences)")
    key_points: list[str] = Field(description="Main takeaways in Chinese")

    # Mindmap
    mindmap_plantuml: str = Field(description="PlantUML mindmap script")
    mindmap_image_path: Optional[str] = Field(
        default=None, description="Path to rendered PNG"
    )

    # Metadata
    word_count: int = Field(description="Original word count")
    reading_time: str = Field(description="Estimated reading time")
    language: str = Field(description="Detected language of original")
    tags: list[str] = Field(description="Auto-generated tags", default_factory=list)


class QuestionResponse(BaseModel):
    """Response schema for answering a question."""

    question: str = Field(description="The original question")
    answer: str = Field(description="Direct answer")
    explanation: str = Field(description="Detailed explanation")
    examples: list[str] = Field(description="Concrete examples", default_factory=list)
    related_topics: list[str] = Field(
        description="Related concepts to explore", default_factory=list
    )
    sources: list[str] = Field(description="Where to learn more", default_factory=list)


class ActionStep(BaseModel):
    """An action step in a plan."""

    step: int = Field(description="Step number")
    action: str = Field(description="What to do")
    expected_outcome: str = Field(description="Expected result")
    dependencies: list[int] = Field(
        description="Step numbers that must be done first", default_factory=list
    )


class IdeaPlanResponse(BaseModel):
    """Response schema for planning an idea."""

    idea: str = Field(description="The original idea")
    goal: str = Field(description="Clear goal definition")
    action_steps: list[ActionStep] = Field(
        description="Concrete action steps", min_length=3
    )
    resources_needed: list[str] = Field(
        description="Tools, skills, or materials required"
    )
    challenges: list[str] = Field(description="Potential obstacles and solutions")
    success_metrics: list[str] = Field(description="How to measure progress")
    first_action: str = Field(description="The very first thing to do")
