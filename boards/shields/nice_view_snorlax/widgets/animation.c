#include <stdlib.h>
#include <zephyr/kernel.h>
#include "animation.h"

LV_IMG_DECLARE(snorlax_01);
LV_IMG_DECLARE(snorlax_02);
LV_IMG_DECLARE(snorlax_03);
LV_IMG_DECLARE(snorlax_04);
LV_IMG_DECLARE(snorlax_05);
LV_IMG_DECLARE(snorlax_06);
LV_IMG_DECLARE(snorlax_07);
LV_IMG_DECLARE(snorlax_08);
LV_IMG_DECLARE(snorlax_09);
LV_IMG_DECLARE(snorlax_10);
LV_IMG_DECLARE(snorlax_11);
LV_IMG_DECLARE(snorlax_12);
LV_IMG_DECLARE(snorlax_13);
LV_IMG_DECLARE(snorlax_14);
LV_IMG_DECLARE(snorlax_15);
LV_IMG_DECLARE(snorlax_16);

const lv_img_dsc_t *anim_imgs[] = {
    &snorlax_01, &snorlax_02, &snorlax_03, &snorlax_04, &snorlax_05, &snorlax_06,
    &snorlax_07, &snorlax_08, &snorlax_09, &snorlax_10, &snorlax_11, &snorlax_12,
    &snorlax_13, &snorlax_14, &snorlax_15, &snorlax_16,
};

void draw_animation(lv_obj_t *canvas) {
#if IS_ENABLED(CONFIG_NICE_VIEW_GEM_ANIMATION)
    lv_obj_t *art = lv_animimg_create(canvas);
    lv_obj_center(art);

    lv_animimg_set_src(art, (const void **)anim_imgs, 16);
    lv_animimg_set_duration(art, CONFIG_NICE_VIEW_GEM_ANIMATION_MS);
    lv_animimg_set_repeat_count(art, LV_ANIM_REPEAT_INFINITE);
    lv_animimg_start(art);
#else
    lv_obj_t *art = lv_img_create(canvas);

    int length = sizeof(anim_imgs) / sizeof(anim_imgs[0]);
    srand(k_uptime_get_32());
    int random_index = rand() % length;

    lv_img_set_src(art, anim_imgs[random_index]);
#endif

    lv_obj_align(art, LV_ALIGN_TOP_LEFT, 36, 0);
}