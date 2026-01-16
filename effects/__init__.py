"""
特效系统

提供各种视频转场特效和动画效果
"""

from effects.base import Effect
from effects.kenburns import effect_registry as kenburns_registry
from effects.transition import effect_registry as transition_registry

# 合并所有特效注册表
effect_registry = {}
effect_registry.update(kenburns_registry)
effect_registry.update(transition_registry)

__all__ = ["Effect", "effect_registry"]
