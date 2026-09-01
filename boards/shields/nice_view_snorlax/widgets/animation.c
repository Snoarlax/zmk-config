#include <stdlib.h>
#include <zephyr/kernel.h>
#include "animation.h"

/* Both defined in assets/snorlax.c, which is generated - the frame count
 * comes from the artwork rather than being fixed here. */
extern const lv_img_dsc_t *snorlax_imgs[];
extern const size_t snorlax_frame_count;

void draw_animation(lv_obj_t *canvas) {
#if IS_ENABLED(CONFIG_NICE_VIEW_GEM_ANIMATION)
    lv_obj_t *art = lv_animimg_create(canvas);
    lv_obj_center(art);

    lv_animimg_set_src(art, (const void **)snorlax_imgs, snorlax_frame_count);
    lv_animimg_set_duration(art, CONFIG_NICE_VIEW_GEM_ANIMATION_MS);
    lv_animimg_set_repeat_count(art, LV_ANIM_REPEAT_INFINITE);
    lv_animimg_start(art);
#else
    lv_obj_t *art = lv_img_create(canvas);

    srand(k_uptime_get_32());
    int random_index = rand() % snorlax_frame_count;

    lv_img_set_src(art, snorlax_imgs[random_index]);
#endif

    lv_obj_align(art, LV_ALIGN_TOP_LEFT, 36, 0);
}
