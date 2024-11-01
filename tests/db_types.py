from pydantic import BaseModel, TypeAdapter

# {'id': 1729390776637, 'name': 'baz', 'mtime_secs': 1729390776, 'usn': -1, 'config': b' \xb8\xa2\xe4\xbd\xaa2B\x05\x10\x01\x1a\x01\x00H\x01\xfa\x0f\x15{"tags":[],"vers":[]}'}
class notetypes(BaseModel):
    id: int
    name: str
    mtime_secs: int
    usn: int
    config: bytes

class CollectionJsonFields:
    class CollectionConfItem(BaseModel):
        nextPos: int
        collapseTime: int
        addToCur: bool
        sched2021: bool
        activeDecks: list[int]
        sortType: str
        timeLim: int
        newSpread: int
        sortBackwards: bool
        creationOffset: int
        dayLearnFirst: bool
        curDeck: int
        estTimes: bool
        schedVer: int
        curModel: int
        dueCounts: bool

    CollectionConf = TypeAdapter(dict[str, CollectionConfItem])

    class DconfField(BaseModel):
        class New(BaseModel):
            bury: bool
            delays: list[float]
            initialFactor: int
            ints: list[int]
            order: int
            perDay: int

        class Rev(BaseModel):
            bury: bool
            ease4: float
            ivlFct: float
            maxIvl: int
            perDay: int
            hardFactor: float

        class Lapse(BaseModel):
            delays: list[float]
            leechAction: int
            leechFails: int
            minInt: int
            mult: float

        id: int
        mod: int
        name: str
        usn: int
        maxTaken: int
        autoplay: bool
        timer: int
        replayq: bool
        new: New
        rev: Rev
        lapse: Lapse
        dyn: bool
        newMix: int
        newPerDayMinimum: int
        interdayLearningMix: int
        reviewOrder: int
        newSortOrder: int
        newGatherPriority: int
        buryInterdayLearning: bool
        fsrsWeights: list[float]
        desiredRetention: float
        ignoreRevlogsBeforeDate: str
        stopTimerOnAnswer: bool
        secondsToShowQuestion: float
        secondsToShowAnswer: float
        questionAction: int
        answerAction: int
        waitForAudio: bool
        sm2Retention: float
        weightSearch: str


    DConf = TypeAdapter(dict[int, DconfField])

    class CollectionDecks:
        class DecksItem(BaseModel):
            id: int
            mod: int
            name: str
            usn: int
            lrnToday: list[int]
            revToday: list[int]
            newToday: list[int]
            timeToday: list[int]
            collapsed: bool
            browserCollapsed: bool
            desc: str
            dyn: int
            conf: int
            extendNew: int
            extendRev: int
            reviewLimit: int | None
            newLimit: int | None
            reviewLimitToday: int | None
            newLimitToday: int | None

        _type_adapter_ = TypeAdapter(dict[int, DecksItem])

        @classmethod
        def __getattr__(cls, attr: str):
            return getattr(cls._type_adapter_, attr)

    class Tmpl(BaseModel):
        name: str
        ord: int
        qfmt: str
        afmt: str
        bqfmt: str
        bafmt: str
        did: int | None
        bfont: str
        bsize: int
        id: int


    class Fld(BaseModel):
        name: str
        ord: int
        sticky: bool
        rtl: bool
        font: str
        size: int
        description: str
        plainText: bool
        collapsed: bool
        excludeFromSearch: bool
        id: int
        tag: str | None
        preventDeletion: bool


    class ModelItem(BaseModel):
        id: int
        name: str
        type: int
        mod: int
        usn: int
        sortf: int
        did: int | None
        # tmpls: list[Tmpl]
        # flds: list[Fld]
        css: str
        latexPre: str
        latexPost: str
        latexsvg: bool
        req: list[list[(int | str) | list[int]]]
        originalStockKind: int


    CollectionModels = TypeAdapter(dict[str, ModelItem])
