import React from 'react';
import {
  View,
  Text,
  TouchableOpacity,
  StyleSheet,
  Dimensions,
} from 'react-native';
import { MaterialCommunityIcons } from '@expo/vector-icons';
import { useTheme } from '../../hooks/useTheme';

const { width: SCREEN_WIDTH } = Dimensions.get('window');

export default function Card({
  children,
  title,
  subtitle,
  icon,
  onPress,
  style,
  variant = 'default',
  contentStyle,
}) {
  const theme = useTheme();

  const getVariantStyles = () => {
    switch (variant) {
      case 'outlined':
        return {
          backgroundColor: theme.colors.transparent,
          borderWidth: 1,
          borderColor: theme.colors.border,
          elevation: 0,
          shadowOpacity: 0,
        };
      case 'elevated':
        return {
          backgroundColor: theme.colors.card,
          borderWidth: 0,
          elevation: 4,
          shadowOpacity: 0.15,
          shadowOffset: { width: 0, height: 4 },
          shadowRadius: 8,
        };
      case 'default':
      default:
        return {
          backgroundColor: theme.colors.card,
          borderWidth: 1,
          borderColor: theme.colors.border,
          elevation: 1,
          shadowOpacity: 0.05,
          shadowOffset: { width: 0, height: 2 },
          shadowRadius: 4,
        };
    }
  };

  const variantStyles = getVariantStyles();

  const hasHeader = title || subtitle || icon;

  const renderContent = () => (
    <>
      {hasHeader && (
        <View style={styles.header}>
          {icon && (
            <View
              style={[
                styles.iconContainer,
                { backgroundColor: theme.colors.primaryLight },
              ]}
            >
              <MaterialCommunityIcons
                name={icon}
                size={20}
                color={theme.colors.primary}
              />
            </View>
          )}
          <View style={styles.titleContainer}>
            {title && (
              <Text
                style={[styles.title, { color: theme.colors.text }]}
                numberOfLines={1}
              >
                {title}
              </Text>
            )}
            {subtitle && (
              <Text
                style={[
                  styles.subtitle,
                  { color: theme.colors.textSecondary },
                ]}
                numberOfLines={1}
              >
                {subtitle}
              </Text>
            )}
          </View>
        </View>
      )}
      <View style={[styles.content, contentStyle]}>{children}</View>
    </>
  );

  if (onPress) {
    return (
      <TouchableOpacity
        onPress={onPress}
        activeOpacity={0.8}
        style={[
          styles.card,
          variantStyles,
          style,
        ]}
      >
        {renderContent()}
      </TouchableOpacity>
    );
  }

  return (
    <View
      style={[
        styles.card,
        variantStyles,
        style,
      ]}
    >
      {renderContent()}
    </View>
  );
}

const styles = StyleSheet.create({
  card: {
    borderRadius: 14,
    marginHorizontal: 16,
    marginVertical: 6,
    overflow: 'hidden',
  },
  header: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingHorizontal: 16,
    paddingTop: 14,
    paddingBottom: 4,
  },
  iconContainer: {
    width: 36,
    height: 36,
    borderRadius: 10,
    justifyContent: 'center',
    alignItems: 'center',
    marginRight: 12,
  },
  titleContainer: {
    flex: 1,
  },
  title: {
    fontSize: 16,
    fontWeight: '700',
  },
  subtitle: {
    fontSize: 13,
    marginTop: 1,
  },
  content: {
    padding: 16,
  },
});
