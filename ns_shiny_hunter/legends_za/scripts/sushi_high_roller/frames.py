from typing import Final

from ns_shiny_hunter.frame import ReferenceFrameEnum, SimpleFrameProcessor, SimpleReferenceFrame, BlurParams

ATTACK_FRAME_PROCESSOR: Final = SimpleFrameProcessor.from_points(
    p1=(1086, 579),
    p2=(1122, 607),
    blur_params=None,
    threshold_params=None
)
DIALOG_FRAME_PROCESSOR: Final = SimpleFrameProcessor.from_points(
    p1=(318, 580),
    p2=(964, 668),
    color_space=None,
    blur_params=None,
    threshold_params=None
)
POKEMON_CENTER_DIALOG_OPTIONS_FRAME_PROCESSOR: Final = SimpleFrameProcessor.from_points(
    p1=(878, 384),
    p2=(1142, 533),
    color_space=None,
    blur_params=None,
    threshold_params=None
)

ITEM_NAME_FRAME_PROCESSOR: Final = SimpleFrameProcessor.from_points(
    p1=(134, 253),
    p2=(467, 278),
    color_space=None,
    blur_params=BlurParams(ksize=(3, 3), sigma_x=0.5),
    threshold_params=None
)
ITEM_QUANTITY_FRAME_PROCESSOR: Final = SimpleFrameProcessor.from_points(
    p1=(624, 235),
    p2=(681, 297),
    color_space=None,
    blur_params=BlurParams(ksize=(3, 3), sigma_x=0.5),
    threshold_params=None
)
QUANTITY_TO_SELL_FRAME_PROCESSOR: Final = SimpleFrameProcessor.from_points(
    p1=(511, 253),
    p2=(556, 279),
    color_space=None,
    blur_params=BlurParams(ksize=(3, 3), sigma_x=0.5),
    threshold_params=None
)
ACCEPT_OFFER_FRAME_PROCESSOR: Final = SimpleFrameProcessor.from_points(
    p1=(949, 437),
    p2=(1141, 530),
    color_space=None,
    blur_params=BlurParams(ksize=(3, 3), sigma_x=0.5),
    threshold_params=None
)


class SushiHighRollerReferenceFrames(ReferenceFrameEnum):
    ENTRANCE_2 = SimpleReferenceFrame.create_from_file(
        __file__, "entrance-2.jpg",
        SimpleFrameProcessor.from_points((558, 162), (713, 208)),
        threshold=10
    )
    ENTRANCE_CONFIRMATION = SimpleReferenceFrame.create_from_file(
        __file__, "entrance-confirmation.jpg",
        SimpleFrameProcessor.from_points((361, 592), (915, 666)),
        threshold=10
    )
    FOLLOW_ME = SimpleReferenceFrame.create_from_file(
        __file__, "follow-me.jpg",
        SimpleFrameProcessor.from_points((363, 592), (710, 621)),
        threshold=10
    )
    BATTLE = SimpleReferenceFrame.create_from_file(
        __file__, "battle.jpg",
        SimpleFrameProcessor.from_points((59, 482), (72, 496)),
        threshold=5
    )
    OUTCOME_FAILURE = SimpleReferenceFrame.create_from_file(
        __file__, "outcome-failure.jpg",
        SimpleFrameProcessor.from_points((361, 592), (824, 616)),
        threshold=10
    )
    OUTCOME_SUCCESS = SimpleReferenceFrame.create_from_file(
        __file__, "outcome-success.jpg",
        SimpleFrameProcessor.from_points((363, 593), (890, 660)),
        threshold=10
    )
    CANNOT_AFFORD = SimpleReferenceFrame.create_from_file(
        __file__, "cannot-afford.jpg",
        SimpleFrameProcessor.from_points((363, 592), (881, 666)),
        threshold=10
    )
    TRAVEL_TO_POKEMON_CENTER = SimpleReferenceFrame.create_from_file(
        __file__, "travel-to-pokemon-center.jpg",
        SimpleFrameProcessor.from_points((873, 128), (1070, 151))
    )
    TRAVEL_TO_POKEMON_CENTER_CONFIRMATION = SimpleReferenceFrame.create_from_file(
        __file__, "travel-to-pokemon-center-confirmation.jpg",
        SimpleFrameProcessor.from_points((363, 593), (663, 622))
    )
    POKEMON_CENTER_DIALOG_START = SimpleReferenceFrame.create_from_file(
        __file__, "pokemon-center-dialog-start.jpg",
        SimpleFrameProcessor.from_points((692, 423), (709, 438))
    )
    SELLING_MENU = SimpleReferenceFrame.create_from_file(
        __file__, "sell-treasures.jpg",
        SimpleFrameProcessor.from_points((474, 30), (764, 76))
    )
    SELL_TREASURES = SimpleReferenceFrame.create_from_file(
        __file__, "sell-treasures.jpg",
        SimpleFrameProcessor.from_points((409, 149), (492, 212)),
        threshold=5
    )
    THIS_POCKET_IS_EMPTY = SimpleReferenceFrame.create_from_file(
        __file__, "this-pocket-is-empty.jpg",
        SimpleFrameProcessor.from_points((277, 400), (468, 424)),
        threshold=5
    )
